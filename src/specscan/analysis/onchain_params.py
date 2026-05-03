from __future__ import annotations

from collections.abc import Callable
from typing import Any

from specscan.etherscan.client import EtherscanClient, EtherscanError
from specscan.schemas import EtherscanSourceBundle, FormalSpec, FormalVariable

PARAMETER_NAME_HINTS = (
    "liquidation",
    "collateralFactor",
    "collateral_factor",
    "closeFactor",
    "close_factor",
    "lltv",
    "ltv",
    "loanToValue",
    "loan_to_value",
    "borrowFactor",
    "borrow_factor",
)

EXACT_PARAMETER_NAMES = {
    "collateralFactorBps",
    "liquidationIncentiveBps",
    "liquidationFeeBps",
    "liquidationFactorBps",
    "liquidationBonus",
    "liquidationBonusBps",
    "liquidationThreshold",
    "liquidationThresholdBps",
    "closeFactor",
    "closeFactorBps",
    "lltv",
}


def resolve_onchain_parameters(
    bundle: EtherscanSourceBundle | None,
    client: EtherscanClient | None,
    address: str,
    *,
    logger: Callable[[str], None] | None = None,
) -> dict[str, str | int | bool]:
    if bundle is None or client is None or not isinstance(bundle.abi, list):
        return {}

    resolved: dict[str, str | int | bool] = {}
    for item in bundle.abi:
        if not _is_relevant_getter(item):
            continue
        name = item["name"]
        output_type = item["outputs"][0].get("type")
        if not isinstance(output_type, str):
            continue
        try:
            raw = client.eth_call(address, _selector_for_zero_arg_function(name))
            resolved[name] = _decode_abi_word(raw, output_type)
        except (EtherscanError, ValueError) as exc:
            if logger:
                logger(f"Parameter read failed {name}: {exc}")
    return resolved


def append_parameter_context(source_context: str, parameters: dict[str, str | int | bool]) -> str:
    if not parameters:
        return source_context
    lines = ["", "Resolved on-chain parameters from zero-argument getters:"]
    for name, value in sorted(parameters.items()):
        lines.append(f"- {name} = {value}")
    return source_context.rstrip() + "\n" + "\n".join(lines)


def inject_parameter_preconditions(
    spec: FormalSpec,
    parameters: dict[str, str | int | bool],
) -> None:
    if not parameters:
        return
    variable_names = {variable.name for variable in spec.variables}
    existing_preconditions = set(spec.preconditions)
    for name, value in parameters.items():
        if isinstance(value, str) and value.startswith("0x"):
            continue
        if isinstance(value, bool):
            expression = f"{name} == {'true' if value else 'false'}"
            symbolic_type = "bool"
        else:
            expression = f"{name} == {value}"
            symbolic_type = "uint"
        if name not in variable_names:
            spec.variables.append(
                FormalVariable(
                    name=name,
                    solidity_type="uint256" if symbolic_type == "uint" else "bool",
                    symbolic_type=symbolic_type,  # type: ignore[arg-type]
                    role="constant",
                    description="Resolved on-chain parameter from verified contract ABI.",
                )
            )
            variable_names.add(name)
        if expression not in existing_preconditions:
            spec.preconditions.append(expression)
            existing_preconditions.add(expression)


def _is_relevant_getter(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    if item.get("type") != "function":
        return False
    name = item.get("name")
    if not isinstance(name, str) or not name:
        return False
    if item.get("inputs") not in ([], None):
        return False
    outputs = item.get("outputs")
    if not isinstance(outputs, list) or len(outputs) != 1:
        return False
    output_type = outputs[0].get("type") if isinstance(outputs[0], dict) else None
    if not isinstance(output_type, str):
        return False
    if not (
        output_type.startswith("uint")
        or output_type.startswith("int")
        or output_type == "bool"
        or output_type == "address"
    ):
        return False
    lowered_name = name.lower()
    if name in EXACT_PARAMETER_NAMES:
        return True
    return any(hint.lower() in lowered_name for hint in PARAMETER_NAME_HINTS)


def _selector_for_zero_arg_function(name: str) -> str:
    return "0x" + keccak256(f"{name}()".encode()).hex()[:8]


def _decode_abi_word(raw: str, output_type: str) -> str | int | bool:
    data = raw[2:] if raw.startswith("0x") else raw
    if len(data) < 64:
        raise ValueError(f"eth_call returned too few bytes: {raw}")
    word = data[:64]
    value = int(word, 16)
    if output_type == "bool":
        return bool(value)
    if output_type == "address":
        return "0x" + word[-40:]
    return value


def keccak256(data: bytes) -> bytes:
    rate = 136
    state = [0] * 25
    padded = bytearray(data)
    padded.append(0x01)
    while len(padded) % rate != rate - 1:
        padded.append(0)
    padded.append(0x80)
    for offset in range(0, len(padded), rate):
        block = padded[offset : offset + rate]
        for lane_index in range(rate // 8):
            lane = int.from_bytes(block[lane_index * 8 : lane_index * 8 + 8], "little")
            state[lane_index] ^= lane
        _keccak_f1600(state)
    output = bytearray()
    while len(output) < 32:
        for lane_index in range(rate // 8):
            output.extend(state[lane_index].to_bytes(8, "little"))
            if len(output) >= 32:
                break
        if len(output) < 32:
            _keccak_f1600(state)
    return bytes(output[:32])


def _keccak_f1600(state: list[int]) -> None:
    rotation_offsets = [
        [0, 36, 3, 41, 18],
        [1, 44, 10, 45, 2],
        [62, 6, 43, 15, 61],
        [28, 55, 25, 21, 56],
        [27, 20, 39, 8, 14],
    ]
    round_constants = [
        0x0000000000000001,
        0x0000000000008082,
        0x800000000000808A,
        0x8000000080008000,
        0x000000000000808B,
        0x0000000080000001,
        0x8000000080008081,
        0x8000000000008009,
        0x000000000000008A,
        0x0000000000000088,
        0x0000000080008009,
        0x000000008000000A,
        0x000000008000808B,
        0x800000000000008B,
        0x8000000000008089,
        0x8000000000008003,
        0x8000000000008002,
        0x8000000000000080,
        0x000000000000800A,
        0x800000008000000A,
        0x8000000080008081,
        0x8000000000008080,
        0x0000000080000001,
        0x8000000080008008,
    ]
    mask = (1 << 64) - 1
    for rc in round_constants:
        c = [
            state[x] ^ state[x + 5] ^ state[x + 10] ^ state[x + 15] ^ state[x + 20]
            for x in range(5)
        ]
        d = [c[(x - 1) % 5] ^ _rotl(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] ^= d[x]
        b = [0] * 25
        for x in range(5):
            for y in range(5):
                b[y + 5 * ((2 * x + 3 * y) % 5)] = _rotl(
                    state[x + 5 * y],
                    rotation_offsets[x][y],
                )
        for x in range(5):
            for y in range(5):
                state[x + 5 * y] = b[x + 5 * y] ^ (
                    (~b[((x + 1) % 5) + 5 * y]) & b[((x + 2) % 5) + 5 * y]
                )
                state[x + 5 * y] &= mask
        state[0] ^= rc


def _rotl(value: int, shift: int) -> int:
    shift %= 64
    return ((value << shift) | (value >> (64 - shift))) & ((1 << 64) - 1)
