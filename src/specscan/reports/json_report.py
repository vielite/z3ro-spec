from __future__ import annotations

from pathlib import Path

from specscan.schemas import CandidatePriority, FindingReport, PrioritizedReport


def write_json_report(
    reports: list[FindingReport],
    out_dir: str | Path,
    *,
    prioritization_summary: dict[str, int | float] | None = None,
    excluded_candidates: list[CandidatePriority] | None = None,
    selected_candidates: list[CandidatePriority] | None = None,
) -> Path:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    output = path / "report.json"
    if prioritization_summary is None:
        output.write_text(
            "[\n"
            + ",\n".join(report.model_dump_json(indent=2) for report in reports)
            + "\n]\n"
        )
        return output

    envelope = PrioritizedReport(
        prioritization_summary=prioritization_summary,
        excluded_candidates=excluded_candidates or [],
        selected_candidates=selected_candidates or [],
        findings=reports,
    )
    output.write_text(envelope.model_dump_json(indent=2) + "\n")
    return output
