"""Glossary lookup tool — parses BBC ubiquitous-language.md once at import.

Source: /Users/brooksjohnson/BCC_NGST_CG/docs/reference/ubiquitous-language.md
Shape: markdown tables (Term | Definition | Aliases) + a "Flagged Ambiguities"
section of prose bullets. Both are queryable — overloaded terms like
"Objective" resolve via the ambiguities section, not the tables.

Parse runs once at module import. File is ~140 lines, stable; no benefit to
per-call I/O.
"""

import os
import re
from pathlib import Path

from pydantic import BaseModel

GLOSSARY_PATH = Path(
    os.getenv(
        "GLOSSARY_PATH",
        str(Path.home() / "BCC_NGST_CG/docs/reference/ubiquitous-language.md"),
    )
)


class GlossaryEntry(BaseModel):
    term: str
    found: bool
    definition: str | None = None
    aliases: list[str] = []
    ambiguity_note: str | None = None


# Match a table-cell term: **Term Name** or **Term Name** (new)
_BOLD_RE = re.compile(r"^\*\*(.+?)\*\*(?:\s*\(new\))?\s*$")
# Match a Flagged Ambiguities bullet: - **"Term"** prose...
_AMBIGUITY_RE = re.compile(r'^-\s+\*\*"([^"]+)"\*\*\s+(.+)$')


def _clean_term(raw: str) -> str | None:
    m = _BOLD_RE.match(raw.strip())
    return m.group(1).strip() if m else None


def _parse_aliases(cell: str) -> list[str]:
    cell = cell.strip()
    if not cell or cell in {"—", "-"}:
        return []
    return [a.strip() for a in cell.split(",") if a.strip()]


def _parse(text: str) -> tuple[dict[str, GlossaryEntry], dict[str, str]]:
    canonical: dict[str, GlossaryEntry] = {}
    ambiguities: dict[str, str] = {}
    in_ambiguities = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        if line.startswith("## "):
            in_ambiguities = line.strip() == "## Flagged Ambiguities"
            continue

        if in_ambiguities:
            m = _AMBIGUITY_RE.match(line)
            if m:
                term = m.group(1).strip()
                note = m.group(2).strip()
                ambiguities[term.lower()] = note
            continue

        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or all(set(c) <= set("-: ") for c in cells):
            continue  # separator row
        term = _clean_term(cells[0])
        if term is None:
            continue  # header row ("Term" cell is not bold)
        definition = cells[1] if len(cells) >= 2 else ""
        aliases = _parse_aliases(cells[2]) if len(cells) >= 3 else []
        canonical[term.lower()] = GlossaryEntry(
            term=term,
            found=True,
            definition=definition,
            aliases=aliases,
        )

    return canonical, ambiguities


_CANONICAL, _AMBIGUITIES = _parse(GLOSSARY_PATH.read_text())


def glossary_lookup(term: str) -> GlossaryEntry:
    """Look up a BBC domain term. Returns canonical definition AND ambiguity note
    when the term appears in both sections (e.g., 'Promotion')."""
    key = term.strip().lower()
    ambiguity = _AMBIGUITIES.get(key)
    canonical = _CANONICAL.get(key)
    if canonical is not None:
        return canonical.model_copy(update={"ambiguity_note": ambiguity})
    if ambiguity is not None:
        return GlossaryEntry(term=term, found=True, ambiguity_note=ambiguity)
    return GlossaryEntry(term=term, found=False)
