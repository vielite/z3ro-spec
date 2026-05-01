from __future__ import annotations

import re
from typing import Any

import z3

from specscan.schemas import CalleeSummary, FormalSpec, VerificationResult
from specscan.solver.expression_parser import ExpressionParseError, parse_expression
from specscan.solver.templates import create_symbols, uint_constraints


def run_z3(
    spec: FormalSpec,
    *,
    allow_incomplete: bool = False,
    allow_unsupported: bool = False,
    timeout_ms: int = 10_000,
) -> VerificationResult:
    warnings: list[str] = []
    if spec.unsupported_features and not allow_unsupported:
        return VerificationResult(
            status="unsupported",
            solver_status="not_run",
            explanation="Spec contains unsupported features.",
            warnings=spec.unsupported_features,
        )
    if not spec.violation_conditions:
        return VerificationResult(
            status="model_incomplete",
            solver_status="not_run",
            explanation="Spec has no violation conditions to assert.",
            warnings=["missing violation_conditions"],
        )

    incomplete_model = bool(spec.missing_context) and not allow_incomplete
    warnings.extend(spec.missing_context)

    solver = z3.Solver()
    solver.set(timeout=timeout_ms)
    symbols = create_symbols(spec)
    for constraint in uint_constraints(spec, symbols):
        solver.add(constraint)

    try:
        prepared_preconditions = list(spec.preconditions)
        prepared_transitions = _prepare_transitions(spec, prepared_preconditions, warnings)
        for expression in prepared_preconditions:
            solver.add(parse_expression(expression, symbols))
        for transition in prepared_transitions:
            _add_transition(solver, transition, symbols)
        violations = [
            parse_expression(condition, symbols)
            for condition in spec.violation_conditions
        ]
        solver.add(z3.Or(*violations) if len(violations) > 1 else violations[0])
    except ExpressionParseError as exc:
        return VerificationResult(
            status="unsupported",
            solver_status="not_run",
            explanation=str(exc),
            warnings=warnings,
        )

    result = solver.check()
    if result == z3.sat:
        if incomplete_model:
            return VerificationResult(
                status="model_incomplete",
                solver_status="sat",
                counterexample=_counterexample(solver.model(), symbols),
                explanation=(
                    "Z3 found a satisfying assignment under an incomplete model. "
                    "Treat this as advisory unless you rerun with --allow-incomplete "
                    "or reduce missing context."
                ),
                warnings=warnings,
            )
        return VerificationResult(
            status="possible_bug",
            solver_status="sat",
            counterexample=_counterexample(solver.model(), symbols),
            explanation="Z3 found a satisfying assignment for at least one violation condition.",
            warnings=warnings,
        )
    if result == z3.unsat:
        if incomplete_model:
            return VerificationResult(
                status="model_incomplete",
                solver_status="unsat",
                counterexample=None,
                explanation=(
                    "Z3 could not satisfy the violation condition under the current "
                    "incomplete model."
                ),
                warnings=warnings,
            )
        return VerificationResult(
            status="not_proven",
            solver_status="unsat",
            counterexample=None,
            explanation="Z3 could not satisfy the violation condition under the encoded model.",
            warnings=warnings,
        )
    return VerificationResult(
        status="model_incomplete",
        solver_status="unknown",
        counterexample=None,
        explanation=f"Z3 returned unknown: {solver.reason_unknown()}",
        warnings=warnings,
    )


def _prepare_transitions(
    spec: FormalSpec,
    preconditions: list[str],
    warnings: list[str],
) -> list[str]:
    prepared: list[str] = []
    for transition in spec.state_transitions:
        replacement = _replace_call_transition_with_callee_formula(
            transition,
            spec.callee_summaries,
            preconditions,
        )
        if replacement is not None:
            warnings.append(
                f"Replaced transition `{transition}` with callee formula `{replacement}`."
            )
            prepared.append(replacement)
            continue
        prepared.append(transition)
    return prepared


def _replace_call_transition_with_callee_formula(
    transition: str,
    callee_summaries: list[CalleeSummary],
    preconditions: list[str],
) -> str | None:
    match = re.fullmatch(
        r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:==|=)\s*([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*;?\s*",
        transition,
    )
    if not match:
        return None
    target_name, callee_name = match.group(1), match.group(2)
    for callee in callee_summaries:
        if callee.name != callee_name or not callee.formula:
            continue
        if target_name not in callee.formula:
            continue
        for assumption in callee.assumptions:
            if assumption not in preconditions:
                preconditions.append(assumption)
        return callee.formula
    return None


def _add_transition(solver: z3.Solver, transition: str, symbols: dict[str, Any]) -> None:
    assignment = _split_assignment(transition)
    if assignment:
        name, expression = assignment
        if name not in symbols:
            symbols[name] = z3.Int(name)
        solver.add(symbols[name] == parse_expression(expression, symbols))
    else:
        solver.add(parse_expression(transition, symbols))


def _split_assignment(transition: str) -> tuple[str, str] | None:
    text = transition.strip().rstrip(";")
    if any(op in text for op in ("==", "!=", ">=", "<=")):
        return None
    match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)", text)
    if not match:
        return None
    return match.group(1), match.group(2)


def _counterexample(model: z3.ModelRef, symbols: dict[str, Any]) -> dict[str, str | int | bool]:
    result: dict[str, str | int | bool] = {}
    for name, symbol in symbols.items():
        value = model.eval(symbol, model_completion=True)
        if z3.is_bool(value):
            result[name] = bool(z3.is_true(value))
        elif z3.is_int_value(value):
            result[name] = int(value.as_long())
        else:
            result[name] = str(value)
    return result
