"""Build a BBC-only subset of the Obsidian vault for container packaging.

Reads from $VAULT_SOURCE (default: ~/Documents/Obsidian Vault/Notes), filters
out personal/learning content per the denylist below, and writes the result to
$VAULT_DEST (default: soto_agent/data/vault/). Also filters index.md so it
only references pages that made it into the subset — preserves the hand-curated
one-liners that drive wiki_search relevance.

Usage:

    # Dry run — print stats, write nothing
    uv run python -m soto_agent.scripts.build_vault_subset --dry-run

    # Real run — wipes VAULT_DEST and rebuilds
    uv run python -m soto_agent.scripts.build_vault_subset

    # Custom paths via env
    VAULT_SOURCE=/path/to/vault VAULT_DEST=/path/to/out uv run python -m soto_agent.scripts.build_vault_subset

Denylist is pattern-based: ship everything except matches. New BBC notes added
to the vault auto-ship on next rebuild. Personal content is excluded by
folder, by exact filename, or by fnmatch glob.
"""

import argparse
import fnmatch
import os
import re
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

VAULT_SOURCE = Path(
    os.getenv(
        "VAULT_SOURCE",
        str(Path.home() / "Documents/Obsidian Vault/Notes"),
    )
)
VAULT_DEST = Path(
    os.getenv(
        "VAULT_DEST",
        str(REPO_ROOT / "soto_agent/data/vault"),
    )
)


# Directories never shipped (relative to vault root, no trailing slash).
DENY_DIRS = {
    "Calmatic",
    "hover-notes-images",
    ".obsidian",
    ".trash",
}

# Top-level .md filenames or fnmatch globs that are excluded.
DENY_FILE_GLOBS = [
    # Personal goal / plan trackers
    "2026 *.md",
    # AI-engineering learning notes
    "AI *.md",
    "Agent *.md",
    "Agents.md",
    "Agentic *.md",
    "LLM *.md",
    "RAG *.md",
    # Specific personal files
    "persona.md",
    "log.md",
]

# Exact filenames that override a deny match — ship even though the glob
# would otherwise exclude them.
ALLOW_OVERRIDES = {
    "AI in Beverage Alcohol Landscape.md",  # BBC-relevant industry intel
}


def is_denied(rel_path: Path) -> bool:
    """Return True if this path should NOT be copied into the subset."""
    parts = rel_path.parts
    # Any ancestor directory denied → deny.
    if parts and parts[0] in DENY_DIRS:
        return True
    # Top-level .md file matching a deny glob (unless allow-listed) → deny.
    if len(parts) == 1 and rel_path.suffix == ".md":
        name = rel_path.name
        if name in ALLOW_OVERRIDES:
            return False
        if any(fnmatch.fnmatch(name, pat) for pat in DENY_FILE_GLOBS):
            return True
    return False


def walk_vault(src: Path) -> tuple[list[Path], list[Path]]:
    """Return (kept, denied) relative paths for every .md file under src."""
    kept: list[Path] = []
    denied: list[Path] = []
    for path in src.rglob("*.md"):
        rel = path.relative_to(src)
        if is_denied(rel):
            denied.append(rel)
        else:
            kept.append(rel)
    return kept, denied


_INDEX_LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


def filter_index(index_text: str, surviving_names: set[str]) -> str:
    """Drop table rows whose [[link]] target does not survive in the subset.

    A row is a line starting with `|` whose first cell contains a [[wikilink]].
    Non-row lines (frontmatter, headers, blank lines) pass through unchanged.

    `surviving_names` should hold both the basename (`Matt Withington`) and the
    full relative path without suffix (`sources/CBD 2026-04-24 Foo`) for every
    page in the subset, since index entries use either form.
    """
    out: list[str] = []
    for line in index_text.splitlines():
        if not line.startswith("|"):
            out.append(line)
            continue
        m = _INDEX_LINK_RE.search(line)
        if not m:
            # Header row / separator row / table-of-contents — keep as-is.
            out.append(line)
            continue
        target = m.group(1).strip()
        if target in surviving_names:
            out.append(line)
        # else: drop the row
    return "\n".join(out) + "\n"


def copy_subset(src: Path, dest: Path, kept: list[Path]) -> None:
    """Wipe dest and copy every kept file from src into dest."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for rel in kept:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, target)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print stats only; do not write to VAULT_DEST.",
    )
    parser.add_argument(
        "--show-denied",
        action="store_true",
        help="List every denied file (large output).",
    )
    parser.add_argument(
        "--show-kept",
        action="store_true",
        help="List every kept file (very large output).",
    )
    args = parser.parse_args()

    if not VAULT_SOURCE.is_dir():
        print(f"VAULT_SOURCE not a directory: {VAULT_SOURCE}", file=sys.stderr)
        return 1

    print(f"Source:      {VAULT_SOURCE}")
    print(f"Destination: {VAULT_DEST}")
    print()

    kept, denied = walk_vault(VAULT_SOURCE)
    surviving_names: set[str] = set()
    for rel in kept:
        stem_path = rel.with_suffix("")
        surviving_names.add(stem_path.name)
        surviving_names.add(str(stem_path))

    print(f"Markdown files in source: {len(kept) + len(denied)}")
    print(f"  kept:   {len(kept)}")
    print(f"  denied: {len(denied)}")

    if args.show_denied:
        print("\nDENIED:")
        for rel in sorted(denied):
            print(f"  {rel}")
    if args.show_kept:
        print("\nKEPT:")
        for rel in sorted(kept):
            print(f"  {rel}")

    # Index filter preview
    index_src = VAULT_SOURCE / "index.md"
    if index_src.is_file():
        original = index_src.read_text()
        filtered = filter_index(original, surviving_names)
        orig_rows = sum(1 for line in original.splitlines() if line.startswith("|"))
        new_rows = sum(1 for line in filtered.splitlines() if line.startswith("|"))
        print(f"\nindex.md rows: {orig_rows} -> {new_rows}")
    else:
        print("\nWARNING: index.md not found in source.")
        filtered = ""

    if args.dry_run:
        print("\n(dry-run — nothing written)")
        return 0

    copy_subset(VAULT_SOURCE, VAULT_DEST, kept)
    if filtered:
        (VAULT_DEST / "index.md").write_text(filtered)

    total_bytes = sum(p.stat().st_size for p in VAULT_DEST.rglob("*") if p.is_file())
    print(f"\nWrote {len(kept)} files ({total_bytes / 1_048_576:.1f} MiB) to {VAULT_DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
