from __future__ import annotations

from specscan.cli import _prioritize_findings
from specscan.schemas import GliderFinding


class FakeTriageLLM:
    def __init__(self) -> None:
        self.calls = 0

    def complete_json(self, _system_prompt, _user_prompt, schema):
        self.calls += 1
        return schema.model_validate(
            {
                "keep": True,
                "confidence": "high",
                "reason": "deposit mints shares and is relevant",
                "fp_categories": [],
                "vulnerability_relevance": "relevant to zero-share deposit vulnerability",
            }
        )


def test_prioritization_stops_triage_after_top_candidates_selected():
    findings = [
        GliderFinding(
            contract=f"0x{i}",
            contract_name=f"Vault{i}",
            sol_function="""
            function deposit(uint256 assets) external returns (uint256 shares) {
                shares = assets * totalSupply / totalAssets;
                balanceOf[msg.sender] += shares;
            }
            """,
            value=float(100 - i),
        )
        for i in range(5)
    ]
    llm = FakeTriageLLM()

    prioritized = _prioritize_findings(
        findings,
        "deposit must not mint zero shares for nonzero assets",
        top_candidates=2,
        min_value=0,
        allow_missing_value=False,
        triage_llm=llm,  # type: ignore[arg-type]
    )

    assert llm.calls == 2
    assert len(prioritized["selected_triaged"]) == 2
    assert prioritized["summary"]["not_evaluated_after_top_candidates_selected"] == 3

