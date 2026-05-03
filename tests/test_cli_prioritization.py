from __future__ import annotations

import pytest
import typer

from specscan.cli import _load_vulnerability_description, _prioritize_findings
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


def test_load_vulnerability_description_reads_text_file(tmp_path):
    vulnerability_file = tmp_path / "vuln.txt"
    vulnerability_file.write_text(
        "deposit must not mint zero shares for nonzero assets\n",
        encoding="utf-8",
    )

    assert (
        _load_vulnerability_description(vulnerability_file)
        == "deposit must not mint zero shares for nonzero assets"
    )


def test_load_vulnerability_description_rejects_empty_file(tmp_path):
    vulnerability_file = tmp_path / "vuln.txt"
    vulnerability_file.write_text("\n", encoding="utf-8")

    with pytest.raises(typer.BadParameter, match="vulnerability file is empty"):
        _load_vulnerability_description(vulnerability_file)


def test_skip_triage_selects_deterministic_candidates_without_llm_calls():
    findings = [
        GliderFinding(
            contract=f"0x{i}",
            contract_name=f"Market{i}",
            sol_function="""
            function liquidate(address user, uint repaidDebt) public {
                require(repaidDebt <= debts[user] * liquidationFactorBps / 10000);
                uint price = oracle.getPrice(address(collateral), collateralFactorBps);
                uint reward = repaidDebt * 1 ether / price;
                reward += reward * liquidationIncentiveBps / 10000;
                debts[user] -= repaidDebt;
                escrow.pay(msg.sender, reward);
            }
            """,
            value=float(100 - i),
        )
        for i in range(4)
    ]
    llm = FakeTriageLLM()

    prioritized = _prioritize_findings(
        findings,
        "Partial liquidation must not create bad debt when liquidation bonus is too high",
        top_candidates=2,
        min_value=0,
        allow_missing_value=False,
        triage_llm=llm,  # type: ignore[arg-type]
        skip_triage=True,
    )

    selected = prioritized["selected_triaged"]
    assert llm.calls == 0
    assert len(selected) == 2
    assert selected[0].reason == "LLM triage skipped; deterministic filters passed"
    assert prioritized["summary"]["llm_triage_skipped"] == 1
