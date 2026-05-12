"""Tests for soto_agent.tools.glossary_lookup.

Pytest conventions used here (since this is the first test file in the repo):

  - Filename starts with `test_` so pytest discovers it.
  - Test functions start with `test_`.
  - Assertions use bare `assert <expr>` — pytest rewrites them at import time
    so the failure message shows the values involved. No `assertEqual`/expect.
  - `@pytest.mark.parametrize` runs the same test body across multiple inputs,
    each as a separate test case in the output.

Run all tests:

    uv sync --extra dev      # one time — installs pytest
    uv run pytest soto_agent/tests/ -v
"""

import pytest

from soto_agent.tools.glossary_lookup import glossary_lookup, GlossaryEntry


# ---------- canonical lookups (table rows) ----------


def test_returns_glossary_entry():
    """Sanity: the tool returns the documented Pydantic type."""
    assert isinstance(glossary_lookup("Account Visit"), GlossaryEntry)


def test_canonical_lookup_exact():
    result = glossary_lookup("Account Visit")
    assert result.found is True
    assert result.definition is not None
    assert "cgcloud__Account_Visit__c" in result.definition
    assert result.ambiguity_note is None


def test_canonical_lookup_is_case_insensitive():
    """Reps will type 'rate of sale' lowercased — must still resolve."""
    lower = glossary_lookup("rate of sale")
    upper = glossary_lookup("RATE OF SALE")
    assert lower.found is True
    assert upper.found is True
    assert lower.definition == upper.definition


def test_term_with_parens_resolves():
    """'Retailer Objective (RO)' is one canonical term — parens are part of the name."""
    result = glossary_lookup("Retailer Objective (RO)")
    assert result.found is True
    assert result.definition is not None


def test_aliases_parsed_from_third_column():
    result = glossary_lookup("Account Caller")
    assert result.found is True
    # Aliases column: "Sales rep, field rep, caller, brewery rep"
    assert "Sales rep" in result.aliases
    assert "field rep" in result.aliases
    assert len(result.aliases) >= 3


def test_em_dash_alias_cell_yields_empty_list():
    """Some rows use '—' to mean 'no aliases'; should not appear as a literal alias."""
    result = glossary_lookup("PRIME")
    assert result.found is True
    assert "—" not in result.aliases


def test_new_suffix_stripped_from_term():
    """Terms tagged '(new)' in source should still match the bare term."""
    result = glossary_lookup("Three-Tier System")
    assert result.found is True
    assert result.definition is not None
    assert "(new)" not in result.term


# ---------- flagged ambiguities (prose bullets) ----------


def test_overloaded_term_returns_ambiguity_note():
    """'Objective' is the canonical overloaded term — must come back via the
    ambiguities path, not the canonical path."""
    result = glossary_lookup("Objective")
    assert result.found is True
    assert result.definition is None
    assert result.ambiguity_note is not None
    assert "overloaded" in result.ambiguity_note


def test_ambiguity_for_promotion():
    result = glossary_lookup("Promotion")
    assert result.found is True
    assert result.ambiguity_note is not None
    assert "WSP" in result.ambiguity_note or "Chain Program" in result.ambiguity_note


# ---------- unknown / edge cases ----------


def test_unknown_term_returns_not_found():
    result = glossary_lookup("Pizza")
    assert result.found is False
    assert result.definition is None
    assert result.aliases == []
    assert result.ambiguity_note is None


def test_whitespace_around_term_is_stripped():
    result = glossary_lookup("  Account Visit  ")
    assert result.found is True


@pytest.mark.parametrize(
    "term",
    [
        "PRIME",
        "SOTO",
        "MOB Objective",
        "Three-Tier System",
        "MULO+C",
        "Circana",
        "Account Caller",
        "Wholesaler Program (WSP)",
    ],
)
def test_known_terms_resolve(term):
    """Spot-check that a representative set of glossary terms parse and resolve."""
    result = glossary_lookup(term)
    assert result.found is True, f"{term!r} did not resolve"
