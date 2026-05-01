from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from specscan.analysis.fp_filters import deterministic_filter
from specscan.llm.client import LLMError, OpenAICompatibleClient
from specscan.llm.prompts import TRIAGE_SYSTEM_PROMPT, TRIAGE_USER_TEMPLATE
from specscan.schemas import GliderFinding, TriagedFinding


def triage_finding(
    finding: GliderFinding,
    vulnerability_description: str,
    llm_client: OpenAICompatibleClient | None = None,
    deterministic_result: TriagedFinding | None = None,
) -> TriagedFinding:
    deterministic = deterministic_result or deterministic_filter(finding, vulnerability_description)
    if not deterministic.keep:
        return deterministic
    if llm_client is None:
        return TriagedFinding(
            original=finding,
            keep=True,
            reason="deterministic filters passed; no triage LLM configured",
            confidence="low",
            fp_categories=deterministic.fp_categories,
            vulnerability_relevance="retained because LLM triage was unavailable",
        )
    prompt = TRIAGE_USER_TEMPLATE.format(
        vulnerability=vulnerability_description,
        contract_name=finding.contract_name or "",
        source_lines=finding.sol_function_source_lines,
        value=finding.value,
        normalized_value=finding.normalized_value,
        function_source=finding.sol_function,
    )
    try:
        response = llm_client.complete_json(TRIAGE_SYSTEM_PROMPT, prompt, TriagedFindingLLMResponse)
    except LLMError as exc:
        return TriagedFinding(
            original=finding,
            keep=False,
            reason=f"triage LLM failed: {exc}",
            confidence="low",
            fp_categories=[*deterministic.fp_categories, "triage_llm_error"],
            vulnerability_relevance="not triaged because the LLM request failed",
        )
    keep = bool(response.keep)
    relevance = response.vulnerability_relevance
    if "needs more context" in response.reason.lower() or "needs more context" in relevance.lower():
        keep = True
    return TriagedFinding(
        original=finding,
        keep=keep,
        reason=response.reason,
        confidence=response.confidence,
        fp_categories=[*deterministic.fp_categories, *response.fp_categories],
        vulnerability_relevance=relevance,
    )


class TriagedFindingLLMResponse(BaseModel):
    keep: bool
    confidence: Literal["high", "medium", "low"]
    reason: str
    fp_categories: list[str] = Field(default_factory=list)
    vulnerability_relevance: str
