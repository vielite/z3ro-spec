from __future__ import annotations

import z3

from specscan.solver.expression_parser import parse_expression


def test_parses_arithmetic_comparison():
    x = z3.Int("x")
    y = z3.Int("y")
    solver = z3.Solver()
    solver.add(parse_expression("x + 2 * y >= 10", {"x": x, "y": y}))
    solver.add(x == 2, y == 4)

    assert solver.check() == z3.sat


def test_parses_min_max_and_implies():
    x = z3.Int("x")
    y = z3.Int("y")
    expr = parse_expression("implies(x > 0, max(x, y) >= min(x, y))", {"x": x, "y": y})
    solver = z3.Solver()
    solver.add(z3.Not(expr))

    assert solver.check() == z3.unsat


def test_parses_llm_style_and_function():
    assets = z3.Int("assets")
    shares = z3.Int("shares")
    expr = parse_expression("and(assets > 0, shares == 0)", {"assets": assets, "shares": shares})
    solver = z3.Solver()
    solver.add(expr)
    solver.add(assets == 1, shares == 0)

    assert solver.check() == z3.sat


def test_parses_constant_exponent_limit():
    x = z3.Int("x")
    expr = parse_expression("x <= 2^8 - 1", {"x": x})
    solver = z3.Solver()
    solver.add(expr)
    solver.add(x == 255)

    assert solver.check() == z3.sat
