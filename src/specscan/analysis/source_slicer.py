from __future__ import annotations

import re


def find_matching_brace(source: str, open_index: int) -> int | None:
    depth = 0
    for index in range(open_index, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def extract_function_by_name(source: str, name: str) -> str | None:
    pattern = re.compile(rf"\bfunction\s+{re.escape(name)}\b[^\{{;]*(?:\{{|;)", re.M)
    match = pattern.search(source)
    if not match:
        return None
    if match.group(0).endswith(";"):
        return match.group(0)
    open_index = source.find("{", match.start())
    close_index = find_matching_brace(source, open_index)
    if close_index is None:
        return None
    return source[match.start() : close_index + 1]


def extract_function_name(function_source: str) -> str:
    match = re.search(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)", function_source)
    return match.group(1) if match else "<unknown>"


def extract_called_identifiers(function_source: str) -> set[str]:
    calls = set(re.findall(r"(?<!function\s)\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", function_source))
    return {
        call
        for call in calls
        if call
        not in {
            "if",
            "for",
            "while",
            "require",
            "revert",
            "emit",
            "return",
            "assert",
            "unchecked",
        }
    }


def extract_modifiers(function_source: str) -> list[str]:
    signature = function_source.split("{", 1)[0]
    returns_split = signature.split("returns", 1)[0]
    after_params = returns_split.rsplit(")", 1)
    if len(after_params) != 2:
        return []
    modifiers = []
    for token in re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\([^)]*\))?", after_params[1]):
        base = token.split("(", 1)[0]
        non_modifiers = {
            "public",
            "external",
            "internal",
            "private",
            "payable",
            "view",
            "pure",
            "virtual",
            "override",
        }
        if base not in non_modifiers:
            modifiers.append(base)
    return modifiers
