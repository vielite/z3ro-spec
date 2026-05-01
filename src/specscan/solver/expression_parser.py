from __future__ import annotations

import ast
import re
from typing import Any

import z3


class ExpressionParseError(ValueError):
    pass


def parse_expression(expression: str, symbols: dict[str, Any]) -> Any:
    normalized = normalize_expression(expression)
    try:
        tree = ast.parse(normalized, mode="eval")
    except SyntaxError as exc:
        raise ExpressionParseError(f"Could not parse expression: {expression}") from exc
    return _convert(tree.body, symbols)


def normalize_expression(expression: str) -> str:
    expr = expression.strip().rstrip(";")
    expr = expr.replace("&&", " and ").replace("||", " or ")
    expr = re.sub(r"(?<=\d)\s*\^\s*(?=\d)", " ** ", expr)
    expr = re.sub(r"(?<![=!<>])!(?!=)", " not ", expr)
    expr = re.sub(r"\band\s*\(", "all_of(", expr)
    expr = re.sub(r"\bor\s*\(", "any_of(", expr)
    expr = re.sub(r"\bnot\s*\(", "not_fn(", expr)
    expr = re.sub(r"\btrue\b", "True", expr, flags=re.I)
    expr = re.sub(r"\bfalse\b", "False", expr, flags=re.I)
    return expr


def _convert(node: ast.AST, symbols: dict[str, Any]) -> Any:
    if isinstance(node, ast.Name):
        if node.id in {"True", "False"}:
            return node.id == "True"
        if node.id not in symbols:
            raise ExpressionParseError(f"Unknown symbol: {node.id}")
        return symbols[node.id]
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, bool)):
            return node.value
        raise ExpressionParseError(f"Unsupported constant: {node.value!r}")
    if isinstance(node, ast.UnaryOp):
        operand = _convert(node.operand, symbols)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.Not):
            return z3.Not(operand)
        raise ExpressionParseError("Unsupported unary operator")
    if isinstance(node, ast.BinOp):
        left = _convert(node.left, symbols)
        right = _convert(node.right, symbols)
        return _convert_binop(node.op, left, right)
    if isinstance(node, ast.BoolOp):
        values = [_convert(value, symbols) for value in node.values]
        if isinstance(node.op, ast.And):
            return z3.And(*values)
        if isinstance(node.op, ast.Or):
            return z3.Or(*values)
        raise ExpressionParseError("Unsupported boolean operator")
    if isinstance(node, ast.Compare):
        return _convert_compare(node, symbols)
    if isinstance(node, ast.Call):
        return _convert_call(node, symbols)
    raise ExpressionParseError(f"Unsupported expression node: {type(node).__name__}")


def _convert_binop(op: ast.operator, left: Any, right: Any) -> Any:
    if isinstance(op, ast.Add):
        return left + right
    if isinstance(op, ast.Sub):
        return left - right
    if isinstance(op, ast.Mult):
        return left * right
    if isinstance(op, ast.Pow):
        if isinstance(left, int) and isinstance(right, int):
            return left**right
        raise ExpressionParseError("Exponentiation is only supported for integer constants")
    if isinstance(op, ast.Div | ast.FloorDiv):
        return left / right
    if isinstance(op, ast.Mod):
        return left % right
    raise ExpressionParseError("Unsupported arithmetic operator")


def _convert_compare(node: ast.Compare, symbols: dict[str, Any]) -> Any:
    left = _convert(node.left, symbols)
    constraints = []
    for op, comparator in zip(node.ops, node.comparators, strict=True):
        right = _convert(comparator, symbols)
        if isinstance(op, ast.GtE):
            constraints.append(left >= right)
        elif isinstance(op, ast.LtE):
            constraints.append(left <= right)
        elif isinstance(op, ast.Gt):
            constraints.append(left > right)
        elif isinstance(op, ast.Lt):
            constraints.append(left < right)
        elif isinstance(op, ast.Eq):
            constraints.append(left == right)
        elif isinstance(op, ast.NotEq):
            constraints.append(left != right)
        else:
            raise ExpressionParseError("Unsupported comparison operator")
        left = right
    return z3.And(*constraints) if len(constraints) > 1 else constraints[0]


def _convert_call(node: ast.Call, symbols: dict[str, Any]) -> Any:
    if not isinstance(node.func, ast.Name):
        raise ExpressionParseError("Only simple function calls are supported")
    name = node.func.id
    args = [_convert(arg, symbols) for arg in node.args]
    if name == "min" and len(args) == 2:
        return z3.If(args[0] <= args[1], args[0], args[1])
    if name == "max" and len(args) == 2:
        return z3.If(args[0] >= args[1], args[0], args[1])
    if name == "floor_div" and len(args) == 2:
        return args[0] / args[1]
    if name == "ceil_div" and len(args) == 2:
        return (args[0] + args[1] - 1) / args[1]
    if name == "implies" and len(args) == 2:
        return z3.Implies(args[0], args[1])
    if name == "all_of" and len(args) >= 1:
        return z3.And(*args)
    if name == "any_of" and len(args) >= 1:
        return z3.Or(*args)
    if name == "not_fn" and len(args) == 1:
        return z3.Not(args[0])
    raise ExpressionParseError(f"Unsupported function call: {name}")
