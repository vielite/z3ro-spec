from __future__ import annotations

import math
from typing import Any

from specscan.schemas import CandidatePriority, GliderFinding, TriagedFinding

CONFIDENCE_RANK = {"high": 0, "medium": 1, "low": 2}


def normalize_value(raw_value: Any) -> tuple[float, str]:
    if raw_value is None:
        return 0.0, "missing"
    if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
        return 0.0, "invalid"
    value = float(raw_value)
    if not math.isfinite(value):
        return 0.0, "invalid"
    if value <= 0:
        return value, "zero_or_negative"
    return value, "valid"


def filter_by_value(
    findings: list[GliderFinding],
    min_value: float,
    allow_missing_value: bool = False,
) -> tuple[list[GliderFinding], list[CandidatePriority]]:
    included: list[GliderFinding] = []
    excluded: list[CandidatePriority] = []

    for finding in findings:
        value = finding.normalized_value
        if finding.value_status == "missing" and allow_missing_value and min_value <= 0:
            included.append(finding)
            continue
        reason = _value_exclusion_reason(finding, min_value)
        if reason:
            excluded.append(
                CandidatePriority(
                    finding=finding,
                    normalized_value=value,
                    deterministic_keep=False,
                    deterministic_reason="not_run_value_excluded",
                    selected_for_verification=False,
                    exclusion_reason=reason,
                )
            )
        else:
            included.append(finding)

    return sort_by_value_desc(included), excluded


def sort_by_value_desc(findings: list[GliderFinding]) -> list[GliderFinding]:
    return sorted(findings, key=lambda finding: finding.normalized_value, reverse=True)


def select_top_candidates(
    triaged: list[TriagedFinding],
    top_n: int,
) -> list[TriagedFinding]:
    eligible = [
        item
        for item in triaged
        if item.original.normalized_value > 0
        and item.keep
        and item.confidence in {"high", "medium"}
        and _has_relevant_triage(item)
    ]
    ranked = sorted(
        eligible,
        key=lambda item: (
            -item.original.normalized_value,
            CONFIDENCE_RANK[item.confidence],
        ),
    )
    return ranked[: max(top_n, 0)]


def priority_from_triage(
    triaged: TriagedFinding,
    *,
    selected: bool,
    rank: int | None = None,
) -> CandidatePriority:
    exclusion_reason = None
    if not selected:
        if not triaged.keep:
            exclusion_reason = "excluded_by_triage_or_deterministic_filter"
        elif triaged.confidence == "low":
            exclusion_reason = "excluded_low_triage_confidence"
        elif not _has_relevant_triage(triaged):
            exclusion_reason = "excluded_not_relevant_to_vulnerability"
        elif triaged.original.normalized_value <= 0:
            exclusion_reason = "excluded_non_positive_value"
        else:
            exclusion_reason = "excluded_not_in_top_candidates"

    deterministic_keep = "likely false positive:" not in triaged.reason.lower()
    return CandidatePriority(
        finding=triaged.original,
        normalized_value=triaged.original.normalized_value,
        deterministic_keep=deterministic_keep,
        deterministic_reason=(
            triaged.reason if not deterministic_keep else "deterministic filters passed"
        ),
        triage_keep=triaged.keep,
        triage_confidence=triaged.confidence,
        triage_reason=triaged.reason,
        selected_for_verification=selected,
        exclusion_reason=exclusion_reason,
        rank=rank,
    )


def _value_exclusion_reason(finding: GliderFinding, min_value: float) -> str | None:
    if finding.value_status == "missing":
        return "excluded_missing_value"
    if finding.value_status == "invalid":
        return "excluded_invalid_value"
    if finding.normalized_value <= min_value:
        if finding.normalized_value <= 0:
            return "excluded_zero_or_negative_value"
        return "excluded_below_min_value"
    return None


def _has_relevant_triage(triaged: TriagedFinding) -> bool:
    text = f"{triaged.vulnerability_relevance} {triaged.reason}".lower()
    irrelevant_markers = (
        "not relevant",
        "irrelevant",
        "unrelated",
        "false positive",
        "no relevance",
    )
    return not any(marker in text for marker in irrelevant_markers)
