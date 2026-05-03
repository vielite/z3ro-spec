from __future__ import annotations

from specscan.analysis.onchain_params import (
    inject_parameter_preconditions,
    keccak256,
    resolve_onchain_parameters,
)
from specscan.schemas import EtherscanSourceBundle, FormalSpec


class FakeEtherscan:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def eth_call(self, address: str, data: str) -> str:
        self.calls.append((address, data))
        values = {
            "0x7f5007ed": 8500,
            "0x6f8dd24c": 1200,
            "0xe031a824": 50,
        }
        return "0x" + values[data].to_bytes(32, "big").hex()


def test_keccak_selector_matches_ethereum_known_value():
    assert keccak256(b"transfer(address,uint256)").hex()[:8] == "a9059cbb"


def test_resolves_relevant_zero_arg_uint_getters():
    bundle = EtherscanSourceBundle(
        address="0xabc",
        contract_name="Market",
        source_code="",
        abi=[
            {
                "type": "function",
                "name": "collateralFactorBps",
                "inputs": [],
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
            },
            {
                "type": "function",
                "name": "liquidationIncentiveBps",
                "inputs": [],
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
            },
            {
                "type": "function",
                "name": "liquidationFeeBps",
                "inputs": [],
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
            },
            {
                "type": "function",
                "name": "debts",
                "inputs": [{"type": "address"}],
                "outputs": [{"type": "uint256"}],
                "stateMutability": "view",
            },
        ],
    )
    client = FakeEtherscan()

    result = resolve_onchain_parameters(bundle, client, "0xabc")  # type: ignore[arg-type]

    assert result == {
        "collateralFactorBps": 8500,
        "liquidationFeeBps": 50,
        "liquidationIncentiveBps": 1200,
    }
    assert len(client.calls) == 3


def test_inject_parameter_preconditions_adds_variables_and_constraints():
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
        violation_conditions=[
            "collateralFactorBps * (10000 + liquidationIncentiveBps) >= 10000 * 10000"
        ],
        z3_encoding_notes=[],
        unsupported_features=[],
        missing_context=[],
        confidence="high",
    )

    inject_parameter_preconditions(
        spec,
        {"collateralFactorBps": 8500, "liquidationIncentiveBps": 1200},
    )

    assert "collateralFactorBps == 8500" in spec.preconditions
    assert "liquidationIncentiveBps == 1200" in spec.preconditions
    assert {variable.name for variable in spec.variables} == {
        "collateralFactorBps",
        "liquidationIncentiveBps",
    }
