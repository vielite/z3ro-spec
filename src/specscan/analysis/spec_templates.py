from __future__ import annotations

from collections.abc import Mapping

from specscan.schemas import FormalSpec, FormalVariable, GliderFinding

BPS_SCALE = 10_000
BPS_SQUARED = BPS_SCALE * BPS_SCALE

PARTIAL_LIQUIDATION_PRECONDITIONS = [
    "debt_before > 0",
    "collateral_before > 0",
    "price > 0",
    "repaidDebt > 0",
    "repaidDebt < debt_before",
    "repaidDebt <= floor_div(debt_before * liquidationFactorBps, 10000)",
    "debt_before > creditLimit_before",
    "collateralFactorBps > 0",
    "collateralFactorBps < 10000",
    "liquidationIncentiveBps >= 0",
    "liquidationFeeBps >= 0",
    "liquidationFactorBps > 0",
    "liquidationFactorBps <= 10000",
    "liquidatorReward + liquidationFee <= collateral_before",
]

PARTIAL_LIQUIDATION_TRANSITIONS = [
    (
        "creditLimit_before = floor_div("
        "collateral_before * price * collateralFactorBps, "
        "1000000000000000000 * 10000)"
    ),
    "debt_after = debt_before - repaidDebt",
    (
        "liquidatorReward = floor_div("
        "floor_div(repaidDebt * 1000000000000000000, price) "
        "* (10000 + liquidationIncentiveBps), 10000)"
    ),
    (
        "liquidationFee = floor_div("
        "floor_div(repaidDebt * 1000000000000000000, price) "
        "* liquidationFeeBps, 10000)"
    ),
    "totalCollateralRemoved = liquidatorReward + liquidationFee",
    "collateral_after = collateral_before - totalCollateralRemoved",
    (
        "creditLimit_after = floor_div("
        "collateral_after * price * collateralFactorBps, "
        "1000000000000000000 * 10000)"
    ),
    "gap_before = debt_before - creditLimit_before",
    "gap_after = debt_after - creditLimit_after",
]

PARTIAL_LIQUIDATION_SAFETY_PROPERTIES = [
    (
        "collateralFactorBps * "
        "(10000 + liquidationIncentiveBps + liquidationFeeBps) < 100000000"
    ),
    "gap_after < gap_before",
    "implies(debt_after > 0, collateral_after > 0)",
]

PARTIAL_LIQUIDATION_VIOLATION_CONDITIONS = [
    (
        "collateralFactorBps * "
        "(10000 + liquidationIncentiveBps + liquidationFeeBps) >= 100000000"
    )
]


def apply_spec_template(
    spec: FormalSpec,
    finding: GliderFinding,
    source_context: str,
    onchain_parameters: Mapping[str, str | int | bool] | None = None,
) -> str | None:
    """Apply a deterministic class-specific formal template when safely detectable.

    The template is intentionally narrow. For v1 it only handles the partial
    liquidation bad-debt class from the LT * (1 + bonus) >= 1 condition.
    """
    if not _looks_like_partial_liquidation(spec, finding, source_context):
        return None

    _ensure_variables(spec, PARTIAL_LIQUIDATION_VARIABLES)
    _merge_unique(spec.preconditions, PARTIAL_LIQUIDATION_PRECONDITIONS)
    spec.state_transitions = list(PARTIAL_LIQUIDATION_TRANSITIONS)
    spec.safety_properties = list(PARTIAL_LIQUIDATION_SAFETY_PROPERTIES)
    _preserve_nonblocking_caveats(spec)
    missing_parameters = _missing_required_liquidation_parameters(
        source_context,
        onchain_parameters or {},
    )
    if missing_parameters:
        spec.violation_conditions = []
        _merge_unique(
            spec.missing_context,
            [
                (
                    "Required on-chain liquidation parameter was not resolved; "
                    f"refusing to let Z3 choose symbolic value: {name}"
                )
                for name in missing_parameters
            ],
        )
    else:
        if not _has_numeric_parameter(onchain_parameters or {}, "liquidationFeeBps"):
            _merge_unique(spec.preconditions, ["liquidationFeeBps == 0"])
        spec.violation_conditions = list(PARTIAL_LIQUIDATION_VIOLATION_CONDITIONS)
    _merge_unique(
        spec.z3_encoding_notes,
        [
            (
                "Applied partial liquidation bad-debt template: tests the joint "
                "basis-point invariant collateralFactorBps * "
                "(10000 + liquidationIncentiveBps + liquidationFeeBps) < 10000^2."
            )
        ],
    )
    spec.vulnerability_class = "partial_liquidation_bad_debt"
    return "partial_liquidation_bad_debt"


PARTIAL_LIQUIDATION_VARIABLES = [
    FormalVariable(
        name="debt_before",
        solidity_type="uint256",
        symbolic_type="uint",
        role="state",
        description="Borrower's debt before the liquidation pass.",
    ),
    FormalVariable(
        name="debt_after",
        solidity_type="uint256",
        symbolic_type="uint",
        role="derived",
        description="Borrower's debt after repaidDebt is applied.",
    ),
    FormalVariable(
        name="collateral_before",
        solidity_type="uint256",
        symbolic_type="uint",
        role="state",
        description="Borrower's collateral balance before liquidation.",
    ),
    FormalVariable(
        name="collateral_after",
        solidity_type="uint256",
        symbolic_type="uint",
        role="derived",
        description="Borrower's collateral balance after seized collateral and fees.",
    ),
    FormalVariable(
        name="repaidDebt",
        solidity_type="uint256",
        symbolic_type="uint",
        role="argument",
        description="Debt amount repaid by the liquidator in this partial pass.",
    ),
    FormalVariable(
        name="price",
        solidity_type="uint256",
        symbolic_type="uint",
        role="external",
        description="Positive oracle price converting collateral to debt units.",
    ),
    FormalVariable(
        name="collateralFactorBps",
        solidity_type="uint256",
        symbolic_type="uint",
        role="constant",
        description="Liquidation threshold/collateral factor in basis points.",
    ),
    FormalVariable(
        name="liquidationIncentiveBps",
        solidity_type="uint256",
        symbolic_type="uint",
        role="constant",
        description="Liquidator bonus in basis points.",
    ),
    FormalVariable(
        name="liquidationFeeBps",
        solidity_type="uint256",
        symbolic_type="uint",
        role="constant",
        description="Protocol liquidation fee in basis points.",
    ),
    FormalVariable(
        name="liquidationFactorBps",
        solidity_type="uint256",
        symbolic_type="uint",
        role="constant",
        description="Close factor limiting how much debt can be repaid.",
    ),
    FormalVariable(
        name="liquidatorReward",
        solidity_type="uint256",
        symbolic_type="uint",
        role="derived",
        description="Collateral transferred to the liquidator, including incentive.",
    ),
    FormalVariable(
        name="liquidationFee",
        solidity_type="uint256",
        symbolic_type="uint",
        role="derived",
        description="Collateral charged as protocol liquidation fee.",
    ),
    FormalVariable(
        name="totalCollateralRemoved",
        solidity_type="uint256",
        symbolic_type="uint",
        role="derived",
        description="Total collateral removed from borrower during liquidation.",
    ),
    FormalVariable(
        name="creditLimit_before",
        solidity_type="uint256",
        symbolic_type="uint",
        role="derived",
        description="Counted collateral before liquidation.",
    ),
    FormalVariable(
        name="creditLimit_after",
        solidity_type="uint256",
        symbolic_type="uint",
        role="derived",
        description="Counted collateral after liquidation.",
    ),
    FormalVariable(
        name="gap_before",
        solidity_type="int256",
        symbolic_type="int",
        role="derived",
        description="Debt minus counted collateral before liquidation.",
    ),
    FormalVariable(
        name="gap_after",
        solidity_type="int256",
        symbolic_type="int",
        role="derived",
        description="Debt minus counted collateral after liquidation.",
    ),
]


def _looks_like_partial_liquidation(
    spec: FormalSpec,
    finding: GliderFinding,
    source_context: str,
) -> bool:
    haystack = " ".join(
        [
            spec.vulnerability_description,
            spec.vulnerability_class,
            spec.target_function,
            finding.sol_function,
            source_context,
        ]
    ).lower()
    liquidation_terms = ("liquidat", "repaiddebt", "repay", "seize", "bad debt")
    parameter_terms = (
        "collateralfactorbps",
        "liquidationincentivebps",
        "liquidationfeebps",
        "liquidationfactorbps",
        "liquidation_bonus",
        "liquidation bonus",
        "close factor",
    )
    article_terms = (
        "partial liquidation",
        "bad debt",
        "health factor",
        "creditlimit",
        "lt *",
        "10000 + liquidationincentivebps",
    )
    return (
        any(term in haystack for term in liquidation_terms)
        and any(term in haystack for term in parameter_terms)
        and any(term in haystack for term in article_terms)
    )


def _missing_required_liquidation_parameters(
    source_context: str,
    onchain_parameters: Mapping[str, str | int | bool],
) -> list[str]:
    required = ["collateralFactorBps", "liquidationIncentiveBps"]
    if "liquidationfeebps" in source_context.lower():
        required.append("liquidationFeeBps")
    return [name for name in required if not _has_numeric_parameter(onchain_parameters, name)]


def _has_numeric_parameter(
    onchain_parameters: Mapping[str, str | int | bool],
    name: str,
) -> bool:
    value = onchain_parameters.get(name)
    return isinstance(value, int) and not isinstance(value, bool)


def _ensure_variables(spec: FormalSpec, variables: list[FormalVariable]) -> None:
    existing = {variable.name for variable in spec.variables}
    for variable in variables:
        if variable.name in existing:
            continue
        spec.variables.append(variable.model_copy(deep=True))
        existing.add(variable.name)


def _merge_unique(target: list[str], items: list[str]) -> None:
    existing = set(target)
    for item in items:
        if item in existing:
            continue
        target.append(item)
        existing.add(item)


def _preserve_nonblocking_caveats(spec: FormalSpec) -> None:
    if spec.missing_context:
        _merge_unique(
            spec.z3_encoding_notes,
            [
                (
                    "LLM missing context treated as non-blocking for the partial "
                    f"liquidation parameter-invariant template: {item}"
                )
                for item in spec.missing_context
            ],
        )
        spec.missing_context = []
    if spec.unsupported_features:
        _merge_unique(
            spec.z3_encoding_notes,
            [
                (
                    "LLM unsupported feature treated as non-blocking for the partial "
                    f"liquidation parameter-invariant template: {item}"
                )
                for item in spec.unsupported_features
            ],
        )
        spec.unsupported_features = []
