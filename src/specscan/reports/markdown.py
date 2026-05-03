from __future__ import annotations

from pathlib import Path

from specscan.schemas import CandidatePriority, FindingReport


def write_markdown_report(
    reports: list[FindingReport],
    out_dir: str | Path,
    *,
    prioritization_summary: dict[str, int | float] | None = None,
    excluded_candidates: list[CandidatePriority] | None = None,
    selected_candidates: list[CandidatePriority] | None = None,
) -> Path:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    output = path / "report.md"
    output.write_text(
        render_markdown_report(
            reports,
            prioritization_summary=prioritization_summary,
            excluded_candidates=excluded_candidates or [],
            selected_candidates=selected_candidates or [],
        )
    )
    return output


def render_markdown_report(
    reports: list[FindingReport],
    *,
    prioritization_summary: dict[str, int | float] | None = None,
    excluded_candidates: list[CandidatePriority] | None = None,
    selected_candidates: list[CandidatePriority] | None = None,
) -> str:
    lines = ["# z3ro-spec Report", ""]
    if prioritization_summary is not None:
        lines.extend(
            _render_prioritization(
                prioritization_summary,
                excluded_candidates or [],
                selected_candidates or [],
            )
        )
    for index, report in enumerate(reports, start=1):
        lines.extend(
            [
                f"## {index}. {report.contract_name or 'Unknown contract'}",
                "",
                f"- Contract address: `{report.contract_address}`",
                f"- Function source lines: `{report.function_source_lines}`",
                f"- Value/TVL: `{report.value}`",
                f"- Vulnerability: {report.vulnerability_description}",
            ]
        )
        if report.triage_result:
            lines.extend(
                [
                    "",
                    "### Triage",
                    "",
                    f"- Keep: `{report.triage_result.keep}`",
                    f"- Confidence: `{report.triage_result.confidence}`",
                    f"- Reason: {report.triage_result.reason}",
                    f"- FP categories: `{report.triage_result.fp_categories}`",
                    f"- Relevance: {report.triage_result.vulnerability_relevance}",
                ]
            )
        if report.formal_spec:
            lines.extend(
                [
                    "",
                    "### Formal Spec",
                    "",
                    f"- Summary: {report.formal_spec.summary}",
                    f"- Missing context: `{report.formal_spec.missing_context}`",
                    f"- Unsupported features: `{report.formal_spec.unsupported_features}`",
                    f"- Safety properties: `{report.formal_spec.safety_properties}`",
                    f"- Violation conditions: `{report.formal_spec.violation_conditions}`",
                ]
            )
        if report.onchain_parameters:
            lines.extend(
                [
                    "",
                    "### On-Chain Parameters",
                    "",
                    *[
                        f"- `{name}`: `{value}`"
                        for name, value in sorted(report.onchain_parameters.items())
                    ],
                ]
            )
        if report.verification:
            lines.extend(
                [
                    "",
                    "### Z3 Result",
                    "",
                    f"- Status: `{report.verification.status}`",
                    f"- Solver status: `{report.verification.solver_status}`",
                    f"- Counterexample: `{report.verification.counterexample}`",
                    f"- Explanation: {report.verification.explanation}",
                    f"- Warnings: `{report.verification.warnings}`",
                ]
            )
        lines.extend(
            [
                "",
                "### Limitations",
                "",
                *[f"- {item}" for item in report.limitations],
                "",
                "### Recommended Manual Review Steps",
                "",
                *[f"- {item}" for item in report.recommended_manual_review_steps],
                "",
            ]
        )
    return "\n".join(lines)


def _render_prioritization(
    summary: dict[str, int | float],
    excluded_candidates: list[CandidatePriority],
    selected_candidates: list[CandidatePriority],
) -> list[str]:
    lines = ["## Candidate Prioritization", ""]
    for key, value in summary.items():
        label = key.replace("_", " ").capitalize()
        lines.append(f"- {label}: `{value}`")
    lines.extend(["", "### Selected Candidates", ""])
    if selected_candidates:
        for candidate in selected_candidates:
            finding = candidate.finding
            lines.append(
                f"- Rank `{candidate.rank}`: `{finding.contract}` "
                f"({finding.contract_name or 'unknown'}), value `{candidate.normalized_value}`, "
                f"confidence `{candidate.triage_confidence}`, reason: {candidate.triage_reason}"
            )
    else:
        lines.append("- None")
    lines.extend(["", "### Excluded Candidates", ""])
    if excluded_candidates:
        for candidate in excluded_candidates:
            finding = candidate.finding
            lines.append(
                f"- `{finding.contract}` ({finding.contract_name or 'unknown'}), "
                f"value `{candidate.normalized_value}`, reason: {candidate.exclusion_reason}"
            )
    else:
        lines.append("- None")
    lines.append("")
    return lines
