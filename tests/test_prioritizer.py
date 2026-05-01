from __future__ import annotations

from specscan.analysis.prioritizer import (
    filter_by_value,
    select_top_candidates,
    sort_by_value_desc,
)
from specscan.schemas import GliderFinding, TriagedFinding


def finding(value: float | None, name: str = "target") -> GliderFinding:
    return GliderFinding(
        contract=f"0x{name}",
        contract_name=name,
        sol_function=f"function {name}() external {{ total += 1; }}",
        value=value,
    )


def triaged(
    value: float,
    *,
    keep: bool = True,
    confidence: str = "high",
    name: str = "target",
) -> TriagedFinding:
    return TriagedFinding(
        original=finding(value, name),
        keep=keep,
        confidence=confidence,  # type: ignore[arg-type]
        reason="relevant to vulnerability",
        fp_categories=[],
        vulnerability_relevance="relevant to vulnerability",
    )


def test_excludes_value_zero():
    included, excluded = filter_by_value([finding(0)], min_value=0)

    assert included == []
    assert excluded[0].exclusion_reason == "excluded_zero_or_negative_value"


def test_excludes_negative_value():
    included, excluded = filter_by_value([finding(-1)], min_value=0)

    assert included == []
    assert excluded[0].exclusion_reason == "excluded_zero_or_negative_value"


def test_excludes_missing_value_by_default():
    included, excluded = filter_by_value([finding(None)], min_value=0)

    assert included == []
    assert excluded[0].exclusion_reason == "excluded_missing_value"


def test_allows_missing_value_when_enabled():
    missing = finding(None)
    included, excluded = filter_by_value([missing], min_value=0, allow_missing_value=True)

    assert included == [missing]
    assert excluded == []


def test_sorts_by_value_descending():
    ordered = sort_by_value_desc([finding(2, "two"), finding(10, "ten"), finding(5, "five")])

    assert [item.normalized_value for item in ordered] == [10, 5, 2]


def test_selects_top_five_candidates_only():
    candidates = [triaged(value, name=f"c{value}") for value in range(1, 8)]

    selected = select_top_candidates(candidates, top_n=5)

    assert len(selected) == 5
    assert [item.original.normalized_value for item in selected] == [7, 6, 5, 4, 3]


def test_does_not_select_low_confidence_triage_results():
    selected = select_top_candidates([triaged(10, confidence="low")], top_n=5)

    assert selected == []


def test_does_not_select_keep_false_triage_results():
    selected = select_top_candidates([triaged(10, keep=False)], top_n=5)

    assert selected == []


def test_prioritizes_high_confidence_over_medium_when_values_tie():
    medium = triaged(10, confidence="medium", name="medium")
    high = triaged(10, confidence="high", name="high")

    selected = select_top_candidates([medium, high], top_n=2)

    assert [item.confidence for item in selected] == ["high", "medium"]

