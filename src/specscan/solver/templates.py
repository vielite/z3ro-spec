from __future__ import annotations

from typing import Any

import z3

from specscan.schemas import FormalSpec


def create_symbols(spec: FormalSpec) -> dict[str, Any]:
    symbols: dict[str, Any] = {}
    for variable in spec.variables:
        if variable.symbolic_type == "bool":
            symbols[variable.name] = z3.Bool(variable.name)
        elif variable.symbolic_type in {"uint", "int", "address", "unknown"}:
            symbols[variable.name] = z3.Int(variable.name)
    return symbols


def uint_constraints(spec: FormalSpec, symbols: dict[str, Any]) -> list[Any]:
    constraints = []
    for variable in spec.variables:
        if variable.symbolic_type in {"uint", "address"} and variable.name in symbols:
            constraints.append(symbols[variable.name] >= 0)
    return constraints

