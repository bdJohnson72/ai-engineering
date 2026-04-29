"""Beer RAG ingest — turns vault markdown into retrievable chunks.

Pipeline (basic mode, Day 1):

    get_vault_docs()         list[Path]    discover .md files in the vault
                                           (sources/, top-level wiki, analyses/, connections/)

    load_document(path)      dict          read one file into {source, type, text}

    strip_frontmatter(text)  str           drop YAML preamble, wikilink-only
                                           opener lines, and low-value sections
                                           (Concepts Extracted, Pages Created, Metadata)

    split_on_headings(text)  list[(h, b)]  split on ## / ### into (heading, body) tuples
                                           (see function docstring for the three cases)

    char_window(body)        list[str]    sliding-window fallback for oversized
                                           sections (MAX_CHUNK_CHARS / OVERLAP_CHARS)

    create_chunks(documents) list[Result]  composes all of the above:
                                              page_content = f"{heading}\\n\\n{window}"
                                              metadata     = {source, type, heading}

Each Result is one retrievable chunk. The heading is prepended to the body on
purpose — it biases the chunk's embedding toward the section's topic AND gives
the answering LLM anchor context when this chunk is later retrieved.

Day 1 carryover (next): create_embeddings + Chroma persistence so the chunks
become a queryable vector store.

Day 3 (planned): replace split_on_headings + char_window with LLM-driven
chunking (Pydantic `Chunk { headline, summary, original_text }` already
scaffolded below for that future swap).

Conventions:
- No LangChain — operating on primitives is the explicit L3 jump.
- text-embedding-3-small for Day 1/2; -large held as a Day-3 controlled
  variable per the sprint plan.

Smoke test: `python sandbox/beer_rag_app/ingest.py` runs `__main__` on the
first 3 vault docs and prints a chunk count + first chunk preview.
"""
from base64 import encode
from pathlib import Path
from typing import Any

from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from chromadb import PersistentClient
from tqdm import tqdm
from litellm import completion
from multiprocessing import Pool
from tenacity import retry, wait_exponential
from tiktoken import _tiktoken
import re
import hashlib

HEADING_PATTERN = re.compile(r'^(#{2,3})\s+(.+?)$', re.MULTILINE)
VAULT_NOTES = Path("~/Documents/Obsidian Vault/Notes").expanduser()
WORKERS = 3
AVERAGE_CHUNK_SIZE = 100
MODEL = "openai/gpt-4.1-nano"
EMBEDDING_MODEL = "text-embedding-3-small"
DB_NAME = str(Path(__file__).parent / "vector_db")
MAX_CHUNK_CHARS = 1500
OVERLAP_CHARS = 150
BATCH_SIZE = 50
COLLECTION_NAME = 'beer_rag'

load_dotenv(override=True)
all_files = ""
openai = OpenAI()
wait = wait_exponential(multiplier=1, min=10, max=240)

# Pydantic
class Result(BaseModel):
    page_content: str
    metadata: dict

# Pydantic
class Chunk(BaseModel):

    headline: str = Field(
        description="A brief heading for this chunk, typically a few words, that is most likely to be surfaced in a query",
    )
    summary: str = Field(
        description="A few sentences summarizing the content of this chunk to answer common questions"
    )
    original_text: str = Field(
        description="The original text of this chunk from the provided document, exactly as is, not changed in any way"
    )

    def as_result(self, document):
        metadata = {"source": document["source"], "type": document["type"]}
        return Result(
            page_content=self.headline + "\n\n" + self.summary + "\n\n" + self.original_text,
            metadata=metadata,
        )

class Chunks(BaseModel):
    chunks: list[Chunk]

def get_vault_docs():
    """
    Load documents from obsidian vault
    """
    source_files = [f for f in (VAULT_NOTES / "sources").glob("*.md")
                    if f.name.startswith(("BBD", "CBD"))]

    # Wiki concept/entity pages (top-level Notes/*.md)
    # Exclude index.md and log.md — those are catalog/log files, not knowledge


    wiki_files = [f for f in VAULT_NOTES.glob("*.md")
              if f.name not in ("index.md", "log.md")
              and not f.name.startswith(".")]

    # Analysis pages — filed answers to previous queries
    analysis_files = list((VAULT_NOTES / "analyses").glob("*.md"))

    # Connection pages — cross-cutting insights linking 2+ concepts
    connection_files = list((VAULT_NOTES / "connections").glob("*.md"))

    # Combine and deduplicate
    all_files = source_files + wiki_files + analysis_files + connection_files
    all_files = list({f.resolve(): f for f in all_files}.values())
    print(all_files[:5])
    return all_files

def make_prompt(document):
    pass

def split_on_headings(text: str) -> list[tuple[str, str]] | list[Any]:
    """Split a markdown document into (heading, body) pairs.

    Pairs each `##` / `###` heading with the prose that follows it, up to
    (but not including) the next heading. The body of one section is the
    text between the END of its heading line and the START of the next
    heading line — or the end of the document, for the last section.

    Three cases this function handles:

      1. **No headings at all** — returns `[('', whole_text)]`. One section,
         empty heading, the entire document as body.
      2. **Text before the first heading** (intro paragraph, leftover YAML,
         a stray wikilink line) — that prefix is emitted first as
         `('', prefix)`, then the regular heading sections follow.
      3. **Normal case** — one `(heading, body)` tuple per heading, in
         document order.

    Both heading and body are stripped of leading/trailing whitespace. The
    heading text excludes the `##` / `###` markers themselves (capture
    group 2 of `HEADING_PATTERN` extracts only the heading text).

    Algorithm note: walks the list of regex Match objects with a look-ahead
    pattern. For match `i`, the body runs from `matches[i].end()` (where
    this heading line ends) to `matches[i + 1].start()` (where the next
    heading begins). The last match has no successor, so its body runs to
    `len(text)` instead.

    Args:
        text: Full content of a markdown document.

    Returns:
        List of `(heading, body)` tuples in document order.

    Examples:
        >>> split_on_headings("## Foo\\n\\nbar\\n\\n## Baz\\n\\nqux")
        [('Foo', 'bar'), ('Baz', 'qux')]
        >>> split_on_headings("intro\\n\\n## Foo\\n\\nbar")
        [('', 'intro'), ('Foo', 'bar')]
        >>> split_on_headings("no headings here")
        [('', 'no headings here')]
    """
    matches = list(HEADING_PATTERN.finditer(text))
    if len(matches) == 0:
        return [('', text.strip())]
    results = []
    if matches[0].start() > 0:
        prefix = text[:matches[0].start()].strip()
        results.append(('', prefix))

    for i, m in enumerate(matches):
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end() : next_start].strip()
        result = (m.group(2).strip(), body)
        results.append(result)
    return results

def char_window(text: str, max_characters: int = MAX_CHUNK_CHARS, overlap : int = OVERLAP_CHARS) -> list[str]:
    if len(text) < max_characters:
        return [text]
    results = []
    for i in range(0, len(text), max_characters - overlap):
        chunk = text[i : i + max_characters]
        results.append(chunk)
    return results




def load_document(path: Path) -> dict:
    rel = path.relative_to(VAULT_NOTES)
    doc_type = rel.parts[0] if len(rel.parts) > 1 else "wiki"
    return {
        "source": str(rel),
        "type": doc_type,
        "text": path.read_text(encoding="utf-8"),
    }


def strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter and low-value metadata sections."""
    # Strip YAML frontmatter block
    text = re.sub(r'^---\n.*?\n---\n*', '', text, flags=re.DOTALL)

    # Strip wikilink-only opening lines (e.g., "[[Foo]] [[Bar]] [[Baz]]")
    text = re.sub(r'^(\[\[.*?\]\]\s*)+\n', '', text)

    # Strip low-value metadata sections that add noise to embeddings
    text = re.sub(
        r'## (Concepts Extracted|Pages Created|Metadata)\n.*?(?=\n## |\Z)',
        '', text, flags=re.DOTALL
    )

    return text.strip()

def create_chunks(documents: list[dict]) -> list[Result]:
    results = []
    for doc in documents:
        doc["text"] = strip_frontmatter(doc["text"])
        splits = split_on_headings(doc["text"])
        for heading, body in splits:
            windows = char_window(body)
            for window in windows:
                page_content = f"{heading}\n\n{window}" if heading else window
                if not page_content.strip():
                    continue
                metadata = {
                    "source": doc["source"],
                    "type": doc["type"],
                    "heading": heading,
                }
                result = Result(page_content=page_content, metadata=metadata)
                results.append(result)
    return results

def crete_embeddings(chunks: list[Result]):
    chroma = PersistentClient(path=DB_NAME)

    # Dedupe by content hash — identical chunks across files would otherwise
    # produce duplicate IDs and Chroma upsert rejects duplicates within a call.
    unique_by_id = {}
    for c in chunks:
        h = hashlib.sha256(c.page_content.encode()).hexdigest()
        if h not in unique_by_id:
            unique_by_id[h] = c
    ids = list(unique_by_id.keys())
    chunks = list(unique_by_id.values())

    texts = [chunk.page_content for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    vectors = []
    for i in tqdm(range(0, len(texts), BATCH_SIZE), desc="embedding"):
        batch = texts[i: i + BATCH_SIZE]
        embeddings = openai.embeddings.create(model=EMBEDDING_MODEL, input=batch).data
        vectors.extend([e.embedding for e in embeddings])

    collection = chroma.get_or_create_collection(COLLECTION_NAME)
    UPSERT_BATCH = 5000  # under Chroma's per-call cap (~5461)
    for i in tqdm(range(0, len(ids), UPSERT_BATCH), desc="upserting"):
        collection.upsert(
            ids=ids[i : i + UPSERT_BATCH],
            embeddings=vectors[i : i + UPSERT_BATCH],
            documents=texts[i : i + UPSERT_BATCH],
            metadatas=metadatas[i : i + UPSERT_BATCH],
        )
    print(f"Vector store created with {collection.count()} documents")







if __name__ == "__main__":
    docs = [load_document(p) for p in get_vault_docs()]
    chunks = create_chunks(docs)
    crete_embeddings(chunks)
    print(f"{len(docs)} docs → {len(chunks)} chunks")
    print("---")
    print(chunks[0].page_content[:300])
    print("---")
    print(chunks[0].metadata)