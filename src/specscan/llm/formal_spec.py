from __future__ import annotations

from specscan.analysis.source_slicer import extract_function_name
from specscan.llm.client import LLMError, OpenAICompatibleClient
from specscan.llm.prompts import FORMAL_SPEC_SYSTEM_PROMPT, FORMAL_SPEC_USER_TEMPLATE
from specscan.schemas import (
    CalleeSummary,
    FormalSpec,
    FormalVariable,
    GliderFinding,
    TriagedFinding,
)


def generate_formal_spec(
    finding: GliderFinding,
    vulnerability_description: str,
    source_context: str,
    triage: TriagedFinding | None = None,
    llm_client: OpenAICompatibleClient | None = None,
) -> FormalSpec:
    function_name = extract_function_name(finding.sol_function)
    if llm_client is None:
        return _fallback_spec(
            finding,
            vulnerability_description,
            function_name,
            reason="formal-verifier LLM was not configured",
        )
    prompt = FORMAL_SPEC_USER_TEMPLATE.format(
        vulnerability=vulnerability_description,
        contract_name=finding.contract_name or "",
        address=finding.contract,
        function_name=function_name,
        triage_notes=triage.model_dump_json(indent=2) if triage else "(none)",
        source_context=source_context,
    )
    try:
        result = llm_client.complete_json(FORMAL_SPEC_SYSTEM_PROMPT, prompt, FormalSpec)
        return result  # type: ignore[return-value]
    except LLMError as exc:
        fallback = _fallback_spec(
            finding,
            vulnerability_description,
            function_name,
            reason="formal-verifier LLM output could not be validated",
        )
        fallback.missing_context.append(f"formal verifier LLM failed: {exc}")
        return fallback


def _fallback_spec(
    finding: GliderFinding,
    vulnerability_description: str,
    function_name: str,
    *,
    reason: str,
) -> FormalSpec:
    return FormalSpec(
        target_contract=finding.contract_name or "",
        target_address=finding.contract,
        target_function=function_name,
        vulnerability_description=vulnerability_description,
        vulnerability_class="generic_state_transition_safety",
        summary=f"Fallback spec created because {reason}.",
        variables=[
            FormalVariable(
                name="x",
                solidity_type="uint256",
                symbolic_type="uint",
                role="unknown",
                description="placeholder variable; replace with LLM or manual specification",
            )
        ],
        callee_summaries=[
            CalleeSummary(
                name=function_name,
                purpose="target function requiring manual modeling",
                formula=None,
                assumptions=[],
            )
        ],
        preconditions=[],
        state_transitions=[],
        safety_properties=[],
        violation_conditions=[],
        z3_encoding_notes=[f"{reason}; manual specification may be required."],
        unsupported_features=[],
        missing_context=["formal verifier LLM output"],
        confidence="low",
    )
