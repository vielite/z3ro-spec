from __future__ import annotations

from specscan.analysis.spec_refinement import refine_oracle_assumptions
from specscan.schemas import FormalSpec, FormalVariable


def test_refine_oracle_assumptions_models_price_as_positive_external():
    spec = FormalSpec(
        target_contract="Market",
        target_address="0xabc",
        target_function="liquidate",
        vulnerability_description="partial liquidation bad debt",
        vulnerability_class="partial_liquidation_bad_debt",
        summary="test",
        variables=[
            FormalVariable(
                name="price",
                solidity_type="uint256",
                symbolic_type="uint",
                role="derived",
                description="oracle price",
            )
        ],
        callee_summaries=[],
        preconditions=[],
        state_transitions=[],
        safety_properties=[],
        violation_conditions=["price > 0"],
        z3_encoding_notes=[],
        unsupported_features=[],
        missing_context=[
            "Exact implementation of oracle.getPrice is not known",
            "Exact behavior of escrow.pay is not known",
        ],
        confidence="high",
    )

    refine_oracle_assumptions(
        spec,
        "uint price = oracle.getPrice(address(collateral), collateralFactorBps);",
    )

    assert "price > 0" in spec.preconditions
    assert spec.missing_context == ["Exact behavior of escrow.pay is not known"]
    assert any("Oracle return values" in note for note in spec.z3_encoding_notes)


def test_refine_oracle_assumptions_adds_price_variable_when_missing():
    spec = FormalSpec(
        target_contract="Market",
        target_address="0xabc",
        target_function="liquidate",
        vulnerability_description="partial liquidation bad debt",
        vulnerability_class="partial_liquidation_bad_debt",
        summary="test",
        variables=[],
        callee_summaries=[],
        preconditions=[],
        state_transitions=[],
        safety_properties=[],
        violation_conditions=["price > 0"],
        z3_encoding_notes=[],
        unsupported_features=[],
        missing_context=[],
        confidence="high",
    )

    refine_oracle_assumptions(spec, "uint256 answer = priceFeed.latestAnswer();")

    assert any(variable.name == "price" for variable in spec.variables)
    assert "price > 0" in spec.preconditions
