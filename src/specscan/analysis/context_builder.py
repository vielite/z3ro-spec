from __future__ import annotations

import re
from dataclasses import dataclass, field

from specscan.analysis.fp_filters import vulnerability_keywords
from specscan.analysis.source_slicer import (
    extract_called_identifiers,
    extract_function_by_name,
    extract_function_name,
    extract_modifiers,
)
from specscan.schemas import EtherscanSourceBundle, GliderFinding


@dataclass
class SourceContext:
    target_function: str
    state_variables: list[str] = field(default_factory=list)
    structs: list[str] = field(default_factory=list)
    enums: list[str] = field(default_factory=list)
    constants: list[str] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    internal_functions: list[str] = field(default_factory=list)
    external_interface_calls: list[str] = field(default_factory=list)
    relevant_helpers: list[str] = field(default_factory=list)

    def as_prompt_text(self) -> str:
        sections = [
            ("TARGET FUNCTION", [self.target_function]),
            ("STATE VARIABLES", self.state_variables),
            ("STRUCTS", self.structs),
            ("ENUMS", self.enums),
            ("CONSTANTS", self.constants),
            ("MODIFIERS", self.modifiers),
            ("INTERNAL FUNCTIONS", self.internal_functions),
            ("EXTERNAL INTERFACE CALLS", self.external_interface_calls),
            ("RELEVANT HELPERS", self.relevant_helpers),
        ]
        return "\n\n".join(
            f"## {title}\n" + ("\n\n".join(items) if items else "(none found)")
            for title, items in sections
        )


def build_source_context(
    finding: GliderFinding,
    bundle: EtherscanSourceBundle | None,
    vulnerability_description: str,
) -> SourceContext:
    full_source = bundle.source_code if bundle else finding.sol_function
    target_name = extract_function_name(finding.sol_function)
    target = extract_function_by_name(full_source, target_name) or finding.sol_function
    keywords = vulnerability_keywords(vulnerability_description)

    # TODO: Replace regex and brace matching with Slither AST/CFG extraction.
    context = SourceContext(
        target_function=target,
        state_variables=_extract_state_variables(full_source, keywords),
        structs=_extract_block_declarations(full_source, "struct", keywords),
        enums=_extract_block_declarations(full_source, "enum", keywords),
        constants=_extract_constants(full_source, keywords),
        modifiers=_extract_modifiers(full_source, target),
        external_interface_calls=_extract_external_interface_calls(target),
    )
    context.internal_functions = _extract_internal_callees(full_source, target, max_depth=2)
    context.relevant_helpers = _extract_relevant_helpers(
        full_source,
        keywords,
        set(context.internal_functions),
    )
    return context


def _extract_state_variables(source: str, keywords: set[str]) -> list[str]:
    declarations: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("//", "function ", "event ", "error ")):
            continue
        if " constant " in f" {stripped} " or " immutable " in f" {stripped} ":
            continue
        declaration_pattern = (
            r"^[A-Za-z_][A-Za-z0-9_<>,\[\]\s]*\s+"
            r"(public|private|internal|external)?\s*"
            r"[A-Za-z_][A-Za-z0-9_]*\s*(=|;)"
        )
        if re.match(declaration_pattern, stripped) and _is_relevant(stripped, keywords):
            declarations.append(stripped)
    return _dedupe_limit(declarations, 40)


def _extract_block_declarations(source: str, keyword: str, keywords: set[str]) -> list[str]:
    results: list[str] = []
    pattern = re.compile(rf"\b{keyword}\s+[A-Za-z_][A-Za-z0-9_]*\s*\{{", re.M)
    for match in pattern.finditer(source):
        block = _balanced_block_from(source, match.start())
        if block and _is_relevant(block, keywords):
            results.append(block)
    return _dedupe_limit(results, 20)


def _extract_constants(source: str, keywords: set[str]) -> list[str]:
    results = []
    for line in source.splitlines():
        is_constant = " constant " in f" {line} " or " immutable " in f" {line} "
        if is_constant and _is_relevant(line, keywords):
            results.append(line.strip())
    return _dedupe_limit(results, 40)


def _extract_modifiers(source: str, target: str) -> list[str]:
    modifier_names = extract_modifiers(target)
    results = []
    for name in modifier_names:
        match = re.search(rf"\bmodifier\s+{re.escape(name)}\b[^\{{]*\{{", source)
        if match:
            block = _balanced_block_from(source, match.start())
            if block:
                results.append(block)
    return _dedupe_limit(results, 20)


def _extract_internal_callees(source: str, target: str, max_depth: int) -> list[str]:
    seen: set[str] = set()
    queue = [(call, 0) for call in extract_called_identifiers(target)]
    results: list[str] = []
    while queue:
        name, depth = queue.pop(0)
        if name in seen or depth >= max_depth:
            continue
        seen.add(name)
        fn = extract_function_by_name(source, name)
        if not fn:
            continue
        if re.search(r"\b(internal|private)\b", fn.split("{", 1)[0]) or name.startswith("_"):
            results.append(fn)
            queue.extend((call, depth + 1) for call in extract_called_identifiers(fn))
    return _dedupe_limit(results, 25)


def _extract_external_interface_calls(target: str) -> list[str]:
    calls = re.findall(r"\b([A-Z][A-Za-z0-9_]*\([^)]*\)\.[A-Za-z_][A-Za-z0-9_]*\([^;]*;)", target)
    dotted = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\([^;]*;)", target)
    return _dedupe_limit([*calls, *dotted], 30)


def _extract_relevant_helpers(
    source: str,
    keywords: set[str],
    already_included: set[str],
) -> list[str]:
    helpers = []
    for match in re.finditer(r"\b(function|library)\s+[A-Za-z_][A-Za-z0-9_]*[^\{]*\{", source):
        block = _balanced_block_from(source, match.start())
        if not block:
            continue
        name_match = re.search(r"\b(?:function|library)\s+([A-Za-z_][A-Za-z0-9_]*)", block)
        name = name_match.group(1) if name_match else ""
        if name not in already_included and _is_relevant(block, keywords):
            helpers.append(block)
    return _dedupe_limit(helpers, 15)


def _balanced_block_from(source: str, start: int) -> str | None:
    open_index = source.find("{", start)
    if open_index == -1:
        return None
    depth = 0
    for index in range(open_index, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    return None


def _is_relevant(text: str, keywords: set[str]) -> bool:
    lowered = re.sub(r"[^a-z0-9_]", "", text.lower())
    return any(keyword in lowered for keyword in keywords)


def _dedupe_limit(items: list[str], limit: int) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item not in seen:
            out.append(item)
            seen.add(item)
        if len(out) >= limit:
            break
    return out
