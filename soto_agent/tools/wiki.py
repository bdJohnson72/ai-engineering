import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel

load_dotenv()

_client = AzureOpenAI(
    api_version=os.environ["AZURE_OPENAI_API_VERSION"],
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    api_key=os.environ["AZURE_OPENAI_API_KEY"],
)
_deployment = os.environ["AZURE_OPENAI_DEPLOYMENT_CHAT"]

VAULT_PATH = Path(os.getenv("VAULT_PATH", str(Path.home() / "Documents/Obsidian Vault/Notes")))

SELECT_PAGES_SYSTEM_PROMPT = """
You are an expert Sales Analyst in the beer and beyond-beer industry.
Given a user question and a wiki index, return the relative paths of up to 8
pages from the index that are most likely to help answer the question.
Return paths exactly as they appear in the index. If nothing is relevant,
return an empty list.
"""

_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


class PageSelection(BaseModel):
    pages: list[str]


class WikiPage(BaseModel):
    path: str
    body: str
    links: list[str]


def _load_index() -> str:
    return (VAULT_PATH / "index.md").read_text()


def _resolve_page_path(name: str) -> Path | None:
    name = name.removesuffix(".md")
    if "/" in name:
        candidate = VAULT_PATH / f"{name}.md"
        return candidate if candidate.is_file() else None
    return next(VAULT_PATH.rglob(f"{name}.md"), None)


def _select_pages(question: str, index_text: str) -> list[str]:
    response = _client.chat.completions.parse(
        model=_deployment,
        messages=[
            {"role": "system", "content": SELECT_PAGES_SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}\n\nIndex:\n{index_text}"},
        ],
        response_format=PageSelection,
        temperature=0,
    )
    raw = response.choices[0].message.parsed.pages
    seen: set[str] = set()
    return [p for p in raw if not (p in seen or seen.add(p))]


def _extract_wikilinks(body: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in _WIKILINK_RE.findall(body):
        name = match.strip()
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def wiki_search(question: str) -> list[str]:
    """Return up to 8 wiki page paths relevant to the question, picked from index.md."""
    return _select_pages(question, _load_index())


def wiki_read(name: str) -> WikiPage:
    """Read a wiki page by name or relative path. Returns body and extracted [[wikilinks]]."""
    path = _resolve_page_path(name)
    if path is None:
        return WikiPage(path=name, body="", links=[])
    body = path.read_text()
    return WikiPage(
        path=str(path.relative_to(VAULT_PATH)),
        body=body,
        links=_extract_wikilinks(body),
    )
