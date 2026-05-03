from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class GliderFinding(BaseModel):
    contract: str
    contract_name: str | None = None
    sol_function: str
    sol_function_source_lines: tuple[int, int] | None = None
    value: float | None = None
    normalized_value: float = 0.0
    value_status: Literal["valid", "missing", "invalid", "zero_or_negative"] = "missing"
    extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("sol_function_source_lines", mode="before")
    @classmethod
    def _coerce_lines(cls, value: Any) -> tuple[int, int] | None:
        if value is None:
            return None
        if isinstance(value, (list, tuple)) and len(value) == 2:
            return (int(value[0]), int(value[1]))
        return None

    @model_validator(mode="after")
    def _derive_value_metadata(self) -> GliderFinding:
        if self.value_status != "missing" or self.normalized_value != 0:
            return self
        if self.value is None:
            return self
        if math.isfinite(self.value) and self.value > 0:
            self.normalized_value = float(self.value)
            self.value_status = "valid"
        elif math.isfinite(self.value):
            self.normalized_value = float(self.value)
            self.value_status = "zero_or_negative"
        else:
            self.value = None
            self.normalized_value = 0.0
            self.value_status = "invalid"
        return self


class TriagedFinding(BaseModel):
    original: GliderFinding
    keep: bool
    reason: str
    confidence: Literal["high", "medium", "low"]
    fp_categories: list[str] = Field(default_factory=list)
    vulnerability_relevance: str


class CandidatePriority(BaseModel):
    finding: GliderFinding
    normalized_value: float
    deterministic_keep: bool
    deterministic_reason: str
    triage_keep: bool | None = None
    triage_confidence: Literal["high", "medium", "low"] | None = None
    triage_reason: str | None = None
    selected_for_verification: bool = False
    exclusion_reason: str | None = None
    rank: int | None = None


class EtherscanSourceBundle(BaseModel):
    address: str
    contract_name: str | None = None
    source_code: str
    abi: list[Any] | str | None = None
    compiler_version: str | None = None
    proxy: bool = False
    implementation: str | None = None


class FormalVariable(BaseModel):
    name: str
    solidity_type: str
    symbolic_type: Literal["uint", "int", "bool", "address", "mapping", "array", "unknown"]
    role: Literal["state", "argument", "constant", "derived", "external", "unknown"]
    description: str

    @field_validator("role", mode="before")
    @classmethod
    def _coerce_role(cls, value: Any) -> str:
        if not isinstance(value, str):
            return "unknown"
        normalized = value.strip().lower()
        role_aliases = {
            "input": "argument",
            "param": "argument",
            "parameter": "argument",
            "arg": "argument",
            "output": "derived",
            "return": "derived",
            "result": "derived",
            "local": "derived",
            "computed": "derived",
            "calculated": "derived",
            "storage": "state",
            "state_variable": "state",
            "const": "constant",
            "immutable": "constant",
            "config": "constant",
            "configuration": "constant",
            "protocol_parameter": "constant",
            "risk_parameter": "constant",
            "admin_parameter": "constant",
            "system_parameter": "constant",
            "global": "constant",
            "formula": "derived",
            "intermediate": "derived",
            "calculation": "derived",
            "calculated_value": "derived",
            "oracle": "external",
            "price": "external",
            "market": "external",
        }
        role = role_aliases.get(normalized, normalized)
        if role in {"state", "argument", "constant", "derived", "external", "unknown"}:
            return role
        return "unknown"

    @field_validator("symbolic_type", mode="before")
    @classmethod
    def _coerce_symbolic_type(cls, value: Any) -> str:
        if not isinstance(value, str):
            return "unknown"
        normalized = value.strip().lower()
        if normalized.startswith("uint"):
            return "uint"
        if normalized.startswith("int"):
            return "int"
        if normalized.startswith("bool"):
            return "bool"
        return normalized


class CalleeSummary(BaseModel):
    name: str
    purpose: str
    formula: str | None = None
    assumptions: list[str] = Field(default_factory=list)

    @field_validator("formula", mode="before")
    @classmethod
    def _coerce_formula(cls, value: Any) -> str | None:
        if value is None:
            return None
        return _formula_item_to_string(value)


class FormalSpec(BaseModel):
    target_contract: str
    target_address: str
    target_function: str
    vulnerability_description: str
    vulnerability_class: str
    summary: str
    variables: list[FormalVariable] = Field(default_factory=list)
    callee_summaries: list[CalleeSummary] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    state_transitions: list[str] = Field(default_factory=list)
    safety_properties: list[str] = Field(default_factory=list)
    violation_conditions: list[str] = Field(default_factory=list)
    z3_encoding_notes: list[str] = Field(default_factory=list)
    unsupported_features: list[str] = Field(default_factory=list)
    missing_context: list[str] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]

    @field_validator(
        "preconditions",
        "state_transitions",
        "safety_properties",
        "violation_conditions",
        "z3_encoding_notes",
        "unsupported_features",
        "missing_context",
        mode="before",
    )
    @classmethod
    def _coerce_string_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return [_formula_item_to_string(value)]
        return [_formula_item_to_string(item) for item in value]

    @field_validator("confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, value: Any) -> str:
        if not isinstance(value, str):
            return "low"
        normalized = value.strip().lower()
        if normalized in {"high", "medium", "low"}:
            return normalized
        return "low"


class VerificationResult(BaseModel):
    status: Literal["possible_bug", "not_proven", "model_incomplete", "unsupported", "error"]
    solver_status: Literal["sat", "unsat", "unknown", "not_run"]
    counterexample: dict[str, str | int | bool] | None = None
    explanation: str
    warnings: list[str] = Field(default_factory=list)


class FindingReport(BaseModel):
    contract_address: str
    contract_name: str | None = None
    function_source_lines: tuple[int, int] | None = None
    value: float | None = None
    vulnerability_description: str
    triage_result: TriagedFinding | None = None
    formal_spec: FormalSpec | None = None
    verification: VerificationResult | None = None
    onchain_parameters: dict[str, str | int | bool] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    recommended_manual_review_steps: list[str] = Field(default_factory=list)


class PrioritizedReport(BaseModel):
    prioritization_summary: dict[str, int | float]
    excluded_candidates: list[CandidatePriority] = Field(default_factory=list)
    selected_candidates: list[CandidatePriority] = Field(default_factory=list)
    findings: list[FindingReport] = Field(default_factory=list)


def _formula_item_to_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return str(value)

    variable = value.get("variable") or value.get("name")
    formula = (
        value.get("formula")
        or value.get("condition")
        or value.get("property")
        or value.get("expression")
        or value.get("invariant")
        or value.get("value")
        or value.get("code")
    )
    if formula is None:
        return str(value)
    formula_text = str(formula)
    if variable and "=" not in formula_text and not any(
        op in formula_text for op in (">", "<", "==", "!=")
    ):
        return f"{variable} = {formula_text}"
    return formula_text
