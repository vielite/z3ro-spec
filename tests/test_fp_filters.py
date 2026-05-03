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


def test_partial_liquidation_candidate_with_repay_amount_is_kept():
    finding = GliderFinding(
        contract="0xabc",
        contract_name="LendingPool",
        sol_function="""
        function liquidate(address borrower, uint256 repayAmount) external {
            uint256 closeFactor = markets[msg.sender].closeFactor;
            uint256 maxRepay = borrowerDebt[borrower] * closeFactor / 1e18;
            uint256 repay = min(repayAmount, maxRepay);
            debt[borrower] -= repay;
            collateral[borrower] -= repay * liquidationBonus / 1e18;
        }
        """,
    )

    result = deterministic_filter(
        finding,
        "Partial liquidation must not create bad debt when LT * (1 + bonus) >= 1",
    )

    assert result.keep is True
    assert "missing_partial_liquidation_mechanics" not in result.fp_categories


def test_partial_liquidation_filter_excludes_non_liquidation_candidate():
    finding = GliderFinding(
        contract="0xabc",
        contract_name="Vault",
        sol_function="""
        function withdraw(uint256 assets) external {
            balances[msg.sender] -= assets;
            token.transfer(msg.sender, assets);
        }
        """,
    )

    result = deterministic_filter(
        finding,
        "Partial liquidation must not create bad debt when liquidation bonus is too high",
    )

    assert result.keep is False
    assert "not_liquidation_mechanism" in result.fp_categories


def test_partial_liquidation_filter_excludes_full_only_liquidation_candidate():
    finding = GliderFinding(
        contract="0xabc",
        contract_name="LendingPool",
        sol_function="""
        function liquidate(address borrower) external {
            uint256 debtToCover = totalDebt[borrower];
            uint256 seizeAllCollateral = collateral[borrower];
            debt[borrower] = 0;
            collateral[borrower] = 0;
        }
        """,
    )

    result = deterministic_filter(
        finding,
        "Partial liquidation must not leave protocol bad debt",
    )

    assert result.keep is False
    assert "full_liquidation_only" in result.fp_categories


def test_partial_liquidation_filter_does_not_affect_other_vulnerability_classes():
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

    categories = classify_false_positive(
        finding,
        "deposit must not mint zero shares for nonzero assets",
    )

    assert "not_liquidation_mechanism" not in categories
    assert "missing_partial_liquidation_mechanics" not in categories
