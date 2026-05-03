from __future__ import annotations

from specscan.schemas import CalleeSummary, FormalSpec, FormalVariable
from specscan.solver.z3_runner import run_z3


def var(name: str) -> FormalVariable:
    return FormalVariable(
        name=name,
        solidity_type="uint256",
        symbolic_type="uint",
        role="unknown",
        description=name,
    )


def spec_with(
    variables: list[str],
    preconditions: list[str],
    transitions: list[str],
    violations: list[str],
) -> FormalSpec:
    return FormalSpec(
        target_contract="Test",
        target_address="0x0",
        target_function="target",
        vulnerability_description="test",
        vulnerability_class="test",
        summary="test",
        variables=[var(name) for name in variables],
        callee_summaries=[],
        preconditions=preconditions,
        state_transitions=transitions,
        safety_properties=[],
        violation_conditions=violations,
        z3_encoding_notes=[],
        unsupported_features=[],
        missing_context=[],
        confidence="high",
    )


def test_borrow_breaks_health_factor_sat():
    spec = spec_with(
        [
            "debt_before",
            "collateral_before",
            "borrow_amount",
            "price",
            "liquidation_threshold",
            "MIN_HEALTH_FACTOR",
            "debt_after",
            "health_after",
        ],
        [
            "debt_before > 0",
            "borrow_amount > 0",
            "price > 0",
            "liquidation_threshold > 0",
            "MIN_HEALTH_FACTOR == 100",
            "collateral_before == 100",
            "debt_before == 100",
            "price == 1",
            "liquidation_threshold == 100",
        ],
        [
            "debt_after = debt_before + borrow_amount",
            "health_after = collateral_before * price * liquidation_threshold / debt_after",
        ],
        ["health_after < MIN_HEALTH_FACTOR"],
    )

    result = run_z3(spec)

    assert result.status == "possible_bug"
    assert result.solver_status == "sat"


def test_deposit_mints_zero_shares_sat():
    spec = spec_with(
        ["assets", "total_supply", "total_assets", "shares"],
        ["assets > 0", "total_supply > 0", "total_assets > total_supply * assets"],
        ["shares = assets * total_supply / total_assets"],
        ["shares == 0"],
    )

    result = run_z3(spec)

    assert result.status == "possible_bug"


def test_amm_invariant_violation_sat():
    spec = spec_with(
        [
            "reserve_x_before",
            "reserve_y_before",
            "reserve_x_after",
            "reserve_y_after",
            "k_before",
            "k_after",
        ],
        [
            "reserve_x_before > 0",
            "reserve_y_before > 0",
            "reserve_x_after > 0",
            "reserve_y_after > 0",
        ],
        [
            "k_before = reserve_x_before * reserve_y_before",
            "k_after = reserve_x_after * reserve_y_after",
        ],
        ["k_after < k_before"],
    )

    result = run_z3(spec)

    assert result.status == "possible_bug"


def test_safe_case_unsat():
    spec = spec_with(
        ["x", "y"],
        ["x >= 0", "y >= x"],
        [],
        ["y < x"],
    )

    result = run_z3(spec)

    assert result.status == "not_proven"
    assert result.solver_status == "unsat"


def test_incomplete_model_still_runs_solver_without_flag():
    spec = spec_with(
        ["assets", "total_supply", "total_assets", "shares"],
        ["assets > 0", "total_supply > 0", "total_assets > total_supply * assets"],
        ["shares = assets * total_supply / total_assets"],
        ["shares == 0"],
    )
    spec.missing_context = ["previewDeposit implementation assumed"]

    result = run_z3(spec)

    assert result.status == "model_incomplete"
    assert result.solver_status == "sat"
    assert result.counterexample is not None


def test_callee_formula_replaces_unsupported_named_call():
    spec = spec_with(
        ["assets_", "totalSupply_before", "totalAssets_before", "shares_"],
        [
            "assets_ > 0",
            "totalSupply_before > 0",
            "totalAssets_before > totalSupply_before * assets_",
        ],
        ["shares_ == previewDeposit(assets_)"],
        ["assets_ > 0 and shares_ == 0"],
    )
    spec.callee_summaries = [
        CalleeSummary(
            name="previewDeposit",
            purpose="share calculation",
            formula="shares_ == floor_div(assets_ * totalSupply_before, totalAssets_before)",
            assumptions=["totalAssets_before > 0", "totalSupply_before > 0"],
        )
    ]

    result = run_z3(spec)

    assert result.status == "possible_bug"
    assert result.solver_status == "sat"


def test_allow_unsupported_skips_bad_formulas_and_runs_supported_violations():
    spec = spec_with(
        ["debt_before", "debt_after", "repaidDebt", "collateralFactorBps"],
        [
            "debt_before > getCreditLimitInternal(user)",
            "repaidDebt > 0",
            "collateralFactorBps == 9200",
        ],
        [
            "debt_after = debt_before - repaidDebt",
            "external_result = oracle.getPrice(user)",
        ],
        [
            "unsupported_call(user) > 0",
            "collateralFactorBps >= 9000",
        ],
    )
    spec.unsupported_features = ["oracle side effects not modeled"]

    result = run_z3(spec, allow_unsupported=True)

    assert result.status == "possible_bug"
    assert result.solver_status == "sat"
    assert any("Skipped unsupported precondition" in warning for warning in result.warnings)
    assert any("Skipped unsupported state transition" in warning for warning in result.warnings)
    assert any("Skipped unsupported violation condition" in warning for warning in result.warnings)


def test_allow_unsupported_reports_when_no_violation_can_be_encoded():
    spec = spec_with(
        ["x"],
        [],
        [],
        ["unsupported_call(user) > 0"],
    )

    result = run_z3(spec, allow_unsupported=True)

    assert result.status == "unsupported"
    assert result.solver_status == "not_run"
    assert result.explanation == "No violation conditions could be encoded for Z3."
