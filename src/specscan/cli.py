from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from specscan.analysis.context_builder import build_source_context
from specscan.analysis.fp_filters import deterministic_filter
from specscan.analysis.onchain_params import (
    append_parameter_context,
    inject_parameter_preconditions,
    resolve_onchain_parameters,
)
from specscan.analysis.prioritizer import (
    filter_by_value,
    priority_from_triage,
    select_top_candidates,
)
from specscan.analysis.spec_refinement import refine_oracle_assumptions
from specscan.analysis.spec_templates import apply_spec_template
from specscan.config import Settings
from specscan.etherscan.client import EtherscanClient, EtherscanError
from specscan.llm.client import OpenAICompatibleClient
from specscan.llm.formal_spec import generate_formal_spec
from specscan.llm.triage import triage_finding
from specscan.loaders.glider_json import load_glider_json
from specscan.reports.json_report import write_json_report
from specscan.reports.markdown import write_markdown_report
from specscan.schemas import (
    CandidatePriority,
    EtherscanSourceBundle,
    FindingReport,
    FormalSpec,
    GliderFinding,
    TriagedFinding,
)
from specscan.solver.z3_runner import run_z3

app = typer.Typer(help="z3ro-spec: vulnerability-agnostic formal-spec assistant")
console = Console(highlight=False)
_BANNER_PRINTED = False

def _emit(message: str, *, style: str | None = None) -> None:
    console.print(
        f"[z3ro-spec] {message}",
        style=style,
        markup=False,
        highlight=False,
        soft_wrap=True,
    )


def log(message: str) -> None:
    _emit(message)


def success(message: str) -> None:
    _emit(message, style="green")


def error(message: str) -> None:
    _emit(message, style="red")


@app.callback()
def _startup(ctx: typer.Context) -> None:
    del ctx
    _print_banner_once()


@app.command()
def triage(
    results_json: Annotated[Path, typer.Argument()],
    vulnerability: Annotated[
        Path,
        typer.Option(
            "--vulnerability",
            "-v",
            help="Path to a text file containing the vulnerability description.",
        ),
    ],
    out: Annotated[Path, typer.Option("--out", "-o")],
    top_candidates: Annotated[
        int,
        typer.Option(
            "--top-candidates",
            help=(
                "Maximum number of high-value, vulnerability-relevant candidates to "
                "send to expensive formal verification."
            ),
        ),
    ] = 5,
    min_value: Annotated[
        float,
        typer.Option(
            "--min-value",
            help="Exclude candidates with value less than or equal to this threshold.",
        ),
    ] = 0.0,
    allow_missing_value: Annotated[
        bool,
        typer.Option(
            "--allow-missing-value",
            help=(
                "Allow candidates with missing value through with value=0. "
                "They are still not eligible for final top-candidate selection."
            ),
        ),
    ] = False,
) -> None:
    vulnerability_description = _load_vulnerability_description(vulnerability)
    findings = load_glider_json(results_json)
    log(f"Loaded {len(findings)} Glider findings")
    llm = _triage_llm()
    prioritized = _prioritize_findings(
        findings,
        vulnerability_description,
        top_candidates=top_candidates,
        min_value=min_value,
        allow_missing_value=allow_missing_value,
        triage_llm=llm,
    )
    if not prioritized["selected_triaged"]:
        error("No value-positive, relevant candidates remained after prioritization.")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "prioritization_summary": prioritized["summary"],
                "excluded_candidates": [
                    item.model_dump(mode="json") for item in prioritized["excluded"]
                ],
                "selected_candidates": [
                    item.model_dump(mode="json") for item in prioritized["selected_priorities"]
                ],
                "triaged_candidates": [
                    item.model_dump(mode="json") for item in prioritized["triaged"]
                ],
            },
            indent=2,
        )
        + "\n"
    )
    success(f"Wrote triage output to {out}")


@app.command("fetch-source")
def fetch_source(
    address: Annotated[str, typer.Argument()],
    out: Annotated[Path, typer.Option("--out", "-o")],
) -> None:
    settings = Settings.from_env()
    if not settings.etherscan_api_key:
        raise typer.BadParameter("ETHERSCAN_API_KEY is required")
    client = EtherscanClient(
        settings.etherscan_api_key,
        chain_id=settings.etherscan_chain_id,
        cache_dir=out,
        timeout_seconds=settings.etherscan_timeout_seconds,
        max_retries=settings.network_retries,
        logger=log,
    )
    bundle = client.fetch_source_bundle(address)
    output = out / f"{address.lower()}.json"
    success(f"Wrote source bundle to {output}")
    log(f"Contract: {bundle.contract_name or '<unknown>'}")


@app.command()
def spec(
    results_json: Annotated[Path, typer.Argument()],
    vulnerability: Annotated[
        Path,
        typer.Option(
            "--vulnerability",
            "-v",
            help="Path to a text file containing the vulnerability description.",
        ),
    ],
    out: Annotated[Path, typer.Option("--out", "-o")],
    top_candidates: Annotated[int, typer.Option("--top-candidates")] = 5,
    min_value: Annotated[float, typer.Option("--min-value")] = 0.0,
    allow_missing_value: Annotated[bool, typer.Option("--allow-missing-value")] = False,
) -> None:
    vulnerability_description = _load_vulnerability_description(vulnerability)
    specs = _generate_specs(
        results_json,
        vulnerability_description,
        top_candidates=top_candidates,
        min_value=min_value,
        allow_missing_value=allow_missing_value,
    )
    out.mkdir(parents=True, exist_ok=True)
    output = out / "specs.json"
    output.write_text(
        "[\n" + ",\n".join(item.model_dump_json(indent=2) for item in specs) + "\n]\n"
    )
    success(f"Wrote {len(specs)} specs to {output}")


@app.command()
def verify(
    spec_json: Annotated[Path, typer.Argument()],
    out: Annotated[Path, typer.Option("--out", "-o")],
    allow_incomplete: Annotated[bool, typer.Option("--allow-incomplete")] = False,
    allow_unsupported: Annotated[bool, typer.Option("--allow-unsupported")] = False,
) -> None:
    specs = _load_specs(spec_json)
    log(f"Loaded {len(specs)} formal spec(s)")
    reports: list[FindingReport] = []
    for index, formal_spec in enumerate(specs, start=1):
        log(
            f"[{index}/{len(specs)}] Running Z3 for "
            f"{formal_spec.target_contract}.{formal_spec.target_function}"
        )
        result = run_z3(
            formal_spec,
            allow_incomplete=allow_incomplete,
            allow_unsupported=allow_unsupported,
        )
        log(
            f"[{index}/{len(specs)}] Z3 result: "
            f"status={result.status} solver={result.solver_status}"
        )
        reports.append(
            FindingReport(
                contract_address=formal_spec.target_address,
                contract_name=formal_spec.target_contract,
                function_source_lines=None,
                value=None,
                vulnerability_description=formal_spec.vulnerability_description,
                formal_spec=formal_spec,
                verification=result,
                limitations=_standard_limitations(),
                recommended_manual_review_steps=_manual_steps(),
            )
        )
    write_json_report(reports, out)
    write_markdown_report(reports, out)
    success(f"Wrote verification reports to {out}")


@app.command()
def scan(
    results_json: Annotated[Path, typer.Argument()],
    vulnerability: Annotated[
        Path,
        typer.Option(
            "--vulnerability",
            "-v",
            help="Path to a text file containing the vulnerability description.",
        ),
    ],
    out: Annotated[Path, typer.Option("--out", "-o")],
    top_candidates: Annotated[
        int,
        typer.Option(
            "--top-candidates",
            help=(
                "Maximum number of high-value, vulnerability-relevant candidates to "
                "send to expensive formal verification."
            ),
        ),
    ] = 5,
    min_value: Annotated[
        float,
        typer.Option(
            "--min-value",
            help="Exclude candidates with value less than or equal to this threshold.",
        ),
    ] = 0.0,
    allow_missing_value: Annotated[
        bool,
        typer.Option(
            "--allow-missing-value",
            help=(
                "Allow candidates with missing value through with value=0. "
                "They are still not eligible for final top-candidate selection."
            ),
        ),
    ] = False,
    allow_incomplete: Annotated[bool, typer.Option("--allow-incomplete")] = False,
    allow_unsupported: Annotated[bool, typer.Option("--allow-unsupported")] = False,
    skip_triage: Annotated[
        bool,
        typer.Option(
            "--skip-triage",
            "--verify",
            help=(
                "Skip lightweight LLM triage and send deterministic, value-positive "
                "candidates directly to formal verification."
            ),
        ),
    ] = False,
) -> None:
    vulnerability_description = _load_vulnerability_description(vulnerability)
    findings = load_glider_json(results_json)
    log(f"Loaded {len(findings)} Glider findings")
    triage_llm = None if skip_triage else _triage_llm()
    if skip_triage:
        success("Skipping LLM triage; deterministic candidates will go to verification")
    prioritized = _prioritize_findings(
        findings,
        vulnerability_description,
        top_candidates=top_candidates,
        min_value=min_value,
        allow_missing_value=allow_missing_value,
        triage_llm=triage_llm,
        skip_triage=skip_triage,
    )
    selected_triaged = prioritized["selected_triaged"]
    if not selected_triaged:
        error("No value-positive, relevant candidates remained after prioritization.")
        write_json_report(
            [],
            out,
            prioritization_summary=prioritized["summary"],
            excluded_candidates=prioritized["excluded"],
            selected_candidates=prioritized["selected_priorities"],
        )
        write_markdown_report(
            [],
            out,
            prioritization_summary=prioritized["summary"],
            excluded_candidates=prioritized["excluded"],
            selected_candidates=prioritized["selected_priorities"],
        )
        return

    formal_llm = _formal_llm()
    etherscan = _etherscan(out / "cache")
    reports: list[FindingReport] = []

    for index, triaged in enumerate(selected_triaged, start=1):
        finding = triaged.original
        success(
            f"[{index}/{len(selected_triaged)}] Selected candidate: "
            f"{_candidate_label(finding)} confidence={triaged.confidence} "
            f"value={finding.normalized_value}"
        )
        log(f"[{index}/{len(selected_triaged)}] Fetching source")
        bundle = _try_fetch_bundle(etherscan, finding.contract)
        onchain_parameters = resolve_onchain_parameters(
            bundle,
            etherscan,
            finding.contract,
            logger=log,
        )
        if onchain_parameters:
            success(
                f"[{index}/{len(selected_triaged)}] Resolved on-chain parameters: "
                + ", ".join(
                    f"{name}={value}" for name, value in sorted(onchain_parameters.items())
                )
            )
        log(f"[{index}/{len(selected_triaged)}] Building source context")
        context = build_source_context(finding, bundle, vulnerability_description)
        source_context = append_parameter_context(context.as_prompt_text(), onchain_parameters)
        log(
            f"[{index}/{len(selected_triaged)}] Source context size: "
            f"{len(source_context)} chars"
        )
        log(f"[{index}/{len(selected_triaged)}] Generating formal spec")
        formal_spec = generate_formal_spec(
            finding,
            vulnerability_description,
            source_context,
            triage=triaged,
            llm_client=formal_llm,
        )
        refine_oracle_assumptions(formal_spec, source_context)
        applied_template = apply_spec_template(
            formal_spec,
            finding,
            source_context,
            onchain_parameters,
        )
        if applied_template:
            success(f"[{index}/{len(selected_triaged)}] Applied template: {applied_template}")
        inject_parameter_preconditions(formal_spec, onchain_parameters)
        log(
            f"[{index}/{len(selected_triaged)}] Formal spec confidence="
            f"{formal_spec.confidence} missing_context={len(formal_spec.missing_context)} "
            f"unsupported={len(formal_spec.unsupported_features)}"
        )
        log(f"[{index}/{len(selected_triaged)}] Running Z3")
        verification = run_z3(
            formal_spec,
            allow_incomplete=allow_incomplete,
            allow_unsupported=allow_unsupported,
        )
        log(
            f"[{index}/{len(selected_triaged)}] Z3 result: "
            f"status={verification.status} solver={verification.solver_status}"
        )
        reports.append(
            FindingReport(
                contract_address=finding.contract,
                contract_name=finding.contract_name,
                function_source_lines=finding.sol_function_source_lines,
                value=finding.value,
                vulnerability_description=vulnerability_description,
                triage_result=triaged,
                formal_spec=formal_spec,
                verification=verification,
                onchain_parameters=onchain_parameters,
                limitations=_standard_limitations(),
                recommended_manual_review_steps=_manual_steps(),
            )
        )
    write_json_report(
        reports,
        out,
        prioritization_summary=prioritized["summary"],
        excluded_candidates=prioritized["excluded"],
        selected_candidates=prioritized["selected_priorities"],
    )
    write_markdown_report(
        reports,
        out,
        prioritization_summary=prioritized["summary"],
        excluded_candidates=prioritized["excluded"],
        selected_candidates=prioritized["selected_priorities"],
    )
    success(f"Wrote scan reports to {out}")


def _generate_specs(
    results_json: Path,
    vulnerability: str,
    *,
    top_candidates: int,
    min_value: float,
    allow_missing_value: bool,
) -> list[FormalSpec]:
    findings = load_glider_json(results_json)
    log(f"Loaded {len(findings)} Glider findings")
    triage_llm = _triage_llm()
    prioritized = _prioritize_findings(
        findings,
        vulnerability,
        top_candidates=top_candidates,
        min_value=min_value,
        allow_missing_value=allow_missing_value,
        triage_llm=triage_llm,
    )
    selected_triaged = prioritized["selected_triaged"]
    if not selected_triaged:
        error("No value-positive, relevant candidates remained after prioritization.")
        return []

    formal_llm = _formal_llm()
    etherscan = _etherscan(Path(".z3ro-spec-cache"))
    specs: list[FormalSpec] = []
    for index, triaged in enumerate(selected_triaged, start=1):
        finding = triaged.original
        log(
            f"[{index}/{len(selected_triaged)}] Generating spec for {_candidate_label(finding)}"
        )
        bundle = _try_fetch_bundle(etherscan, finding.contract)
        onchain_parameters = resolve_onchain_parameters(
            bundle,
            etherscan,
            finding.contract,
            logger=log,
        )
        context = build_source_context(finding, bundle, vulnerability)
        source_context = append_parameter_context(context.as_prompt_text(), onchain_parameters)
        formal_spec = generate_formal_spec(
            finding,
            vulnerability,
            source_context,
            triage=triaged,
            llm_client=formal_llm,
        )
        refine_oracle_assumptions(formal_spec, source_context)
        apply_spec_template(formal_spec, finding, source_context, onchain_parameters)
        inject_parameter_preconditions(formal_spec, onchain_parameters)
        specs.append(formal_spec)
    return specs


def _load_vulnerability_description(path: Path) -> str:
    if not path.is_file():
        raise typer.BadParameter(
            f"vulnerability file does not exist or is not a file: {path}"
        )
    try:
        description = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise typer.BadParameter(f"failed to read vulnerability file {path}: {exc}") from exc
    if not description:
        raise typer.BadParameter("vulnerability file is empty")
    return description


def _prioritize_findings(
    findings: list[GliderFinding],
    vulnerability: str,
    *,
    top_candidates: int,
    min_value: float,
    allow_missing_value: bool,
    triage_llm: OpenAICompatibleClient | None,
    skip_triage: bool = False,
) -> dict[str, object]:
    value_filtered, excluded = filter_by_value(
        findings,
        min_value=min_value,
        allow_missing_value=allow_missing_value,
    )
    log(
        "Value filter: "
        f"input={len(findings)} remaining={len(value_filtered)} "
        f"excluded={len(excluded)} min_value={min_value} "
        f"allow_missing_value={allow_missing_value}"
    )

    triaged: list[TriagedFinding] = []
    deterministic_excluded = 0
    skipped_after_selection = 0
    for index, finding in enumerate(value_filtered, start=1):
        log(
            f"[{index}/{len(value_filtered)}] Deterministic filters for "
            f"{_candidate_label(finding)}"
        )
        deterministic = deterministic_filter(finding, vulnerability)
        if not deterministic.keep:
            deterministic_excluded += 1
            log(
                f"[{index}/{len(value_filtered)}] Deterministic excluded "
                f"{_candidate_label(finding)} reason={deterministic.reason}"
            )
            excluded.append(
                CandidatePriority(
                    finding=finding,
                    normalized_value=finding.normalized_value,
                    deterministic_keep=False,
                    deterministic_reason=deterministic.reason,
                    selected_for_verification=False,
                    exclusion_reason="excluded_by_deterministic_filters",
                )
            )
            continue
        success(
            f"[{index}/{len(value_filtered)}] Deterministic kept "
            f"{_candidate_label(finding)}"
        )
        if skip_triage:
            triaged_result = TriagedFinding(
                original=finding,
                keep=True,
                reason="LLM triage skipped; deterministic filters passed",
                confidence="high",
                fp_categories=deterministic.fp_categories,
                vulnerability_relevance=(
                    "Candidate selected for formal verification without LLM triage."
                ),
            )
        else:
            log(f"[{index}/{len(value_filtered)}] Starting LLM triage")
            triaged_result = triage_finding(
                finding,
                vulnerability,
                triage_llm,
                deterministic_result=deterministic,
            )
        (success if triaged_result.keep else error)(
            f"[{index}/{len(value_filtered)}] Triage result "
            f"{_candidate_label(finding)} keep={triaged_result.keep} "
            f"confidence={triaged_result.confidence} reason={triaged_result.reason}"
        )
        triaged.append(triaged_result)

        selected_so_far = select_top_candidates(triaged, top_candidates)
        if top_candidates > 0 and len(selected_so_far) >= top_candidates:
            remaining = value_filtered[index:]
            skipped_after_selection = len(remaining)
            if remaining:
                log(
                    "Top candidate target reached; skipping "
                    f"{len(remaining)} lower-value candidate(s) before LLM triage"
                )
                excluded.extend(
                    CandidatePriority(
                        finding=remaining_finding,
                        normalized_value=remaining_finding.normalized_value,
                        deterministic_keep=False,
                        deterministic_reason="not_run_top_candidates_already_selected",
                        selected_for_verification=False,
                        exclusion_reason="not_evaluated_after_top_candidates_selected",
                    )
                    for remaining_finding in remaining
                )
            break

    all_eligible = select_top_candidates(triaged, len(triaged))
    selected_triaged = select_top_candidates(triaged, top_candidates)
    selected_ids = {id(item) for item in selected_triaged}

    selected_priorities = [
        priority_from_triage(item, selected=True, rank=index)
        for index, item in enumerate(selected_triaged, start=1)
    ]
    excluded.extend(
        priority_from_triage(item, selected=False)
        for item in triaged
        if id(item) not in selected_ids
    )

    summary = {
        "total_input_candidates": len(findings),
        "excluded_due_to_missing_invalid_zero_or_low_value": len(findings)
        - len(value_filtered),
        "remaining_after_value_filter": len(value_filtered),
        "excluded_by_deterministic_filters": deterministic_excluded,
        "excluded_by_llm_triage": len(triaged) - len(all_eligible),
        "not_evaluated_after_top_candidates_selected": skipped_after_selection,
        "selected_for_formal_verification": len(selected_triaged),
        "top_candidates_requested": top_candidates,
        "min_value": min_value,
        "llm_triage_skipped": int(skip_triage),
    }
    success(
        "Prioritization selected "
        f"{len(selected_triaged)} of {len(findings)} candidates for formal verification"
    )
    for index, item in enumerate(selected_triaged, start=1):
        success(
            f"Top candidate #{index}: {_candidate_label(item.original)} "
            f"value={item.original.normalized_value} confidence={item.confidence}"
        )
    return {
        "summary": summary,
        "excluded": excluded,
        "selected_priorities": selected_priorities,
        "triaged": triaged,
        "selected_triaged": selected_triaged,
    }


def _load_specs(path: Path) -> list[FormalSpec]:
    raw = json.loads(path.read_text())
    if isinstance(raw, list):
        return [FormalSpec.model_validate(item) for item in raw]
    return [FormalSpec.model_validate(raw)]


def _triage_llm() -> OpenAICompatibleClient | None:
    settings = Settings.from_env()
    if not (
        settings.triage_llm_api_key
        and settings.triage_llm_base_url
        and settings.triage_llm_model
    ):
        error("Triage LLM not configured; deterministic retained findings will stay open")
        return None
    success(
        "Triage LLM configured: "
        f"model={settings.triage_llm_model} base_url={settings.triage_llm_base_url} "
        f"timeout={settings.llm_timeout_seconds:.0f}s retries={settings.network_retries}"
    )
    return OpenAICompatibleClient(
        settings.triage_llm_api_key,
        settings.triage_llm_base_url,
        settings.triage_llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.network_retries,
        logger=log,
    )


def _formal_llm() -> OpenAICompatibleClient | None:
    settings = Settings.from_env()
    if not (
        settings.formal_verifier_llm_api_key
        and settings.formal_verifier_llm_base_url
        and settings.formal_verifier_llm_model
    ):
        error("Formal verifier LLM not configured; fallback incomplete specs will be emitted")
        return None
    success(
        "Formal verifier LLM configured: "
        f"model={settings.formal_verifier_llm_model} "
        f"base_url={settings.formal_verifier_llm_base_url} "
        f"timeout={settings.llm_timeout_seconds:.0f}s retries={settings.network_retries}"
    )
    return OpenAICompatibleClient(
        settings.formal_verifier_llm_api_key,
        settings.formal_verifier_llm_base_url,
        settings.formal_verifier_llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        max_retries=settings.network_retries,
        logger=log,
    )


def _etherscan(cache_dir: Path) -> EtherscanClient | None:
    settings = Settings.from_env()
    if not settings.etherscan_api_key:
        log(
            "ETHERSCAN_API_KEY not configured; source expansion will use Glider snippets only"
        )
        return None
    success(
        "Etherscan configured: "
        f"chain_id={settings.etherscan_chain_id} "
        f"cache_dir={cache_dir} timeout={settings.etherscan_timeout_seconds:.0f}s "
        f"retries={settings.network_retries}"
    )
    return EtherscanClient(
        settings.etherscan_api_key,
        chain_id=settings.etherscan_chain_id,
        cache_dir=cache_dir,
        timeout_seconds=settings.etherscan_timeout_seconds,
        max_retries=settings.network_retries,
        logger=log,
    )


def _try_fetch_bundle(client: EtherscanClient | None, address: str) -> EtherscanSourceBundle | None:
    if client is None:
        return None
    try:
        return client.fetch_source_bundle(address)
    except EtherscanError as exc:
        error(f"Etherscan fetch failed for {address}: {exc}")
        return None


def _standard_limitations() -> list[str]:
    return [
        "Z3 checks only the encoded formal model, not full Solidity or EVM semantics.",
        "sat means possible_bug, never verified_bug.",
        "Heuristic source slicing may miss relevant context until Slither integration is added.",
    ]


def _manual_steps() -> list[str]:
    return [
        "Review missing_context and unsupported_features before trusting solver output.",
        "Compare each formula against Solidity source and protocol documentation.",
        "Manually validate any counterexample against real units, rounding, and access control.",
    ]


def _candidate_label(finding: GliderFinding) -> str:
    return (
        f"{finding.contract_name or '<unknown>'}@{finding.contract} "
        f"lines={finding.sol_function_source_lines}"
    )


def _print_banner_once() -> None:
    global _BANNER_PRINTED
    if _BANNER_PRINTED:
        return
    banner_path = Path(__file__).resolve().parents[2] / "art.txt"
    if banner_path.exists():
        console.print(banner_path.read_text(), markup=False, highlight=False, soft_wrap=True)
    _BANNER_PRINTED = True
