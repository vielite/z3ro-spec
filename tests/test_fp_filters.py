from __future__ import annotations

from specscan.analysis.fp_filters import classify_false_positive, deterministic_filter
from specscan.schemas import GliderFinding


def test_delegate_only_is_filtered():
    finding = GliderFinding(
        contract="0xabc",
        contract_name="Proxy",
        sol_function="function liquidate(address user) external { _delegate(impl); }",
    )

    result = deterministic_filter(finding, "liquidation must not leave bad debt")

    assert result.keep is False
    assert "delegate_only" in result.fp_categories


def test_relevant_state_changing_candidate_is_kept():
    finding = GliderFinding(
        contract="0xabc",
        contract_name="Vault",
        sol_function="""
        function deposit(uint256 assets) external returns (uint256 shares) {
            shares = assets * totalSupply / totalAssets;
            balanceOf[msg.sender] += shares;
        }
        """,
    )

    categories = classify_false_positive(finding, "deposit must not mint zero shares")

    assert "no_arithmetic_calls_or_state_writes" not in categories
    assert "no_relevant_identifiers" not in categories

