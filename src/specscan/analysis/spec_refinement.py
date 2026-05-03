from __future__ import annotations

import re

from specscan.schemas import FormalSpec, FormalVariable

ORACLE_CALL_PATTERN = re.compile(
    r"\b(?:[A-Za-z_][A-Za-z0-9_]*Oracle|oracle|priceFeed|price_feed)"
    r"\s*(?:\([^)]*\))?\s*\.\s*"
    r"(?:getPrice|price|getAssetPrice|latestAnswer|latestRoundData|peek|read|getRate)"
    r"\s*\(",
    re.I,
)

PRICE_VARIABLE_NAMES = {
    "price",
    "oraclePrice",
    "oracle_price",
    "collateralPrice",
    "collateral_price",
    "exchangeRate",
    "exchange_rate",
}


def refine_oracle_assumptions(spec: FormalSpec, source_context: str) -> None:
    if not ORACLE_CALL_PATTERN.search(source_context):
        return

    _remove_oracle_missing_context(spec)
    price_variables = _price_variables(spec)
    for name in sorted(price_variables):
        _ensure_variable(spec, name)
        _ensure_precondition(spec, f"{name} > 0")
    _ensure_note(
        spec,
        "Oracle return values are modeled as positive symbolic external inputs unless "
        "resolved from on-chain state.",
    )


def _remove_oracle_missing_context(spec: FormalSpec) -> None:
    oracle_markers = ("oracle", "price feed", "pricefeed", "getprice", "latestanswer")
    retained = []
    for item in spec.missing_context:
        lowered = item.lower()
        if any(marker in lowered for marker in oracle_markers):
            continue
        retained.append(item)
    spec.missing_context = retained


def _price_variables(spec: FormalSpec) -> set[str]:
    names = {
        variable.name
        for variable in spec.variables
        if variable.name in PRICE_VARIABLE_NAMES
        or "price" in variable.name.lower()
        or "rate" in variable.name.lower()
    }
    if not names:
        names.add("price")
    return names


def _ensure_variable(spec: FormalSpec, name: str) -> None:
    if any(variable.name == name for variable in spec.variables):
        return
    spec.variables.append(
        FormalVariable(
            name=name,
            solidity_type="uint256",
            symbolic_type="uint",
            role="external",
            description="Positive symbolic oracle return value.",
        )
    )


def _ensure_precondition(spec: FormalSpec, expression: str) -> None:
    if expression not in spec.preconditions:
        spec.preconditions.append(expression)


def _ensure_note(spec: FormalSpec, note: str) -> None:
    if note not in spec.z3_encoding_notes:
        spec.z3_encoding_notes.append(note)
