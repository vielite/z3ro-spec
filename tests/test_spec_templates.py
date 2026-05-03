from __future__ import annotations

from specscan.analysis.onchain_params import inject_parameter_preconditions
from specscan.analysis.spec_templates import apply_spec_template
from specscan.schemas import FormalSpec, FormalVariable, GliderFinding
from specscan.solver.z3_runner import run_z3


def _finding(source: str = "function liquidate(address user, uint repaidDebt)") -> GliderFinding:
    return GliderFinding(
        contract="0x123",
        contract_name="Market",
        sol_function=source,
        sol_function_source_lines=(1, 20),
        value=1_000_000,
    )


def _spec(description: str = "partial liquidation must not create bad debt") -> FormalSpec:
    return FormalSpec(
        target_contract="Market",
        target_address="0x123",
        target_function="liquidate",
        vulnerability_description=description,
        vulnerability_class="liquidation",
        summary="LLM generated liquidation spec",
        variables=[
            FormalVariable(
                name="collateralFactorBps",
                solidity_type="uint256",
                symbolic_type="uint",
                role="constant",
                description="collateral factor",
            )
        ],
        callee_summaries=[],
        preconditions=["price >= 0"],
        state_transitions=["debt_after = debt_before - repaidDebt"],
        safety_properties=[],
        violation_conditions=["price == 0"],
        z3_encoding_notes=[],
        unsupported_features=[],
        missing_context=[],
        confidence="high",
    )


def test_partial_liquidation_template_replaces_weak_llm_violation():
    spec = _spec()
    spec.missing_context = ["Exact escrow callback behavior is not modeled."]
    spec.unsupported_features = ["External transfer side effects are abstracted."]

    applied = apply_spec_template(
        spec,
        _finding(),
        (
            "function liquidate(...) { uint incentive = liquidationIncentiveBps; "
            "uint factor = liquidationFactorBps; uint cf = collateralFactorBps; }"
        ),
        {
            "collateralFactorBps": 9200,
            "liquidationIncentiveBps": 400,
            "liquidationFactorBps": 10000,
        },
    )

    assert applied == "partial_liquidation_bad_debt"
    assert "price > 0" in spec.preconditions
    assert "repaidDebt < debt_before" in spec.preconditions
    assert "debt_after = debt_before - repaidDebt" in spec.state_transitions
    assert spec.violation_conditions == [
        (
            "collateralFactorBps * "
            "(10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000"
        )
    ]
    assert {variable.name for variable in spec.variables} >= {
        "collateralFactorBps",
        "liquidationIncentiveBps",
        "liquidationFeeBps",
        "liquidationFactorBps",
        "debt_before",
        "collateral_before",
        "creditLimit_before",
        "gap_after",
    }
    assert spec.missing_context == []
    assert spec.unsupported_features == []
    assert any("missing context treated as non-blocking" in note for note in spec.z3_encoding_notes)
    assert any(
        "unsupported feature treated as non-blocking" in note
        for note in spec.z3_encoding_notes
    )


def test_partial_liquidation_template_safe_parameters_are_unsat():
    spec = _spec()
    apply_spec_template(
        spec,
        _finding(),
        (
            "partial liquidation uses collateralFactorBps, liquidationIncentiveBps, "
            "liquidationFeeBps, liquidationFactorBps, and repaidDebt"
        ),
        {
            "collateralFactorBps": 8500,
            "liquidationIncentiveBps": 1000,
            "liquidationFeeBps": 0,
            "liquidationFactorBps": 7500,
        },
    )
    inject_parameter_preconditions(
        spec,
        {
            "collateralFactorBps": 8500,
            "liquidationIncentiveBps": 1000,
            "liquidationFeeBps": 0,
            "liquidationFactorBps": 7500,
        },
    )

    result = run_z3(spec, allow_incomplete=True, allow_unsupported=True)

    assert result.status == "not_proven"
    assert result.solver_status == "unsat"


def test_partial_liquidation_template_unsafe_parameters_are_sat():
    spec = _spec()
    apply_spec_template(
        spec,
        _finding(),
        (
            "partial liquidation uses collateralFactorBps, liquidationIncentiveBps, "
            "liquidationFeeBps, liquidationFactorBps, and repaidDebt"
        ),
        {
            "collateralFactorBps": 9700,
            "liquidationIncentiveBps": 500,
            "liquidationFeeBps": 0,
            "liquidationFactorBps": 5000,
        },
    )
    inject_parameter_preconditions(
        spec,
        {
            "collateralFactorBps": 9700,
            "liquidationIncentiveBps": 500,
            "liquidationFeeBps": 0,
            "liquidationFactorBps": 5000,
        },
    )

    result = run_z3(spec, allow_incomplete=True, allow_unsupported=True)

    assert result.status == "possible_bug"
    assert result.solver_status == "sat"


def test_partial_liquidation_template_blocks_unresolved_fee_parameter():
    spec = _spec()

    apply_spec_template(
        spec,
        _finding(),
        (
            "partial liquidation uses collateralFactorBps, liquidationIncentiveBps, "
            "liquidationFeeBps, liquidationFactorBps, and repaidDebt"
        ),
        {
            "collateralFactorBps": 9200,
            "liquidationIncentiveBps": 400,
            "liquidationFactorBps": 10000,
        },
    )

    result = run_z3(spec, allow_incomplete=True, allow_unsupported=True)

    assert spec.violation_conditions == []
    assert any("liquidationFeeBps" in item for item in spec.missing_context)
    assert result.status == "model_incomplete"
    assert result.solver_status == "not_run"


def test_partial_liquidation_template_defaults_absent_fee_to_zero():
    spec = _spec()

    apply_spec_template(
        spec,
        _finding(),
        (
            "partial liquidation uses collateralFactorBps, "
            "liquidationIncentiveBps, liquidationFactorBps, and repaidDebt"
        ),
        {
            "collateralFactorBps": 9200,
            "liquidationIncentiveBps": 400,
            "liquidationFactorBps": 10000,
        },
    )

    assert "liquidationFeeBps == 0" in spec.preconditions
    assert spec.violation_conditions


def test_partial_liquidation_template_does_not_apply_to_unrelated_specs():
    spec = _spec("deposit must not mint zero shares for nonzero assets")

    applied = apply_spec_template(
        spec,
        _finding("function deposit(uint assets) returns (uint shares)"),
        "function deposit(uint assets) returns (uint shares)",
    )

    assert applied is None
    assert spec.violation_conditions == ["price == 0"]
