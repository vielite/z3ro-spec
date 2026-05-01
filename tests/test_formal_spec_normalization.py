from __future__ import annotations

from specscan.schemas import FormalSpec


def test_formal_spec_accepts_common_llm_formula_objects():
    spec = FormalSpec.model_validate(
        {
            "target_contract": "Vault",
            "target_address": "0x0",
            "target_function": "deposit",
            "vulnerability_description": "deposit must not mint zero shares",
            "vulnerability_class": "zero_shares",
            "summary": "test",
            "variables": [
                {
                    "name": "assets",
                    "solidity_type": "uint256",
                    "symbolic_type": "uint256",
                    "role": "input",
                    "description": "deposit assets",
                },
                {
                    "name": "shares",
                    "solidity_type": "uint256",
                    "symbolic_type": "uint",
                    "role": "output",
                    "description": "minted shares",
                },
            ],
            "callee_summaries": [],
            "preconditions": [{"condition": "assets > 0", "description": "nonzero"}],
            "state_transitions": [{"variable": "shares", "formula": "assets / 2"}],
            "safety_properties": [{"property": "implies(assets > 0, shares > 0)"}],
            "violation_conditions": [{"condition": "and(assets > 0, shares == 0)"}],
            "z3_encoding_notes": [{"note": "integer model"}],
            "unsupported_features": [],
            "missing_context": [],
            "confidence": "HIGH",
        }
    )

    assert spec.variables[0].role == "argument"
    assert spec.variables[0].symbolic_type == "uint"
    assert spec.variables[1].role == "derived"
    assert spec.preconditions == ["assets > 0"]
    assert spec.state_transitions == ["shares = assets / 2"]
    assert spec.safety_properties == ["implies(assets > 0, shares > 0)"]
    assert spec.violation_conditions == ["and(assets > 0, shares == 0)"]
    assert spec.confidence == "high"

