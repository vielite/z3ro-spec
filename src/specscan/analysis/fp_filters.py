from __future__ import annotations

import re

from specscan.schemas import GliderFinding, TriagedFinding

STOPWORDS = {
    "a",
    "an",
    "the",
    "must",
    "not",
    "make",
    "after",
    "before",
    "than",
    "from",
    "with",
    "without",
    "remain",
    "always",
    "below",
    "above",
    "minimum",
    "maximum",
}

STATE_TRANSITION_TERMS = {
    "borrow",
    "withdraw",
    "deposit",
    "redeem",
    "swap",
    "mint",
    "burn",
    "claim",
    "liquidation",
    "liquidate",
    "transition",
    "accounting",
    "state",
    "update",
}


def deterministic_filter(
    finding: GliderFinding,
    vulnerability_description: str,
) -> TriagedFinding:
    categories = classify_false_positive(finding, vulnerability_description)
    keep = not _has_hard_reject(categories)
    reason = "deterministic filters passed"
    confidence = "low"
    relevance = "candidate retained for LLM triage"
    if categories:
        reason = "likely false positive: " + ", ".join(categories)
        relevance = "deterministic filters found weak or missing relevance"
        confidence = "medium" if keep else "high"
    return TriagedFinding(
        original=finding,
        keep=keep,
        reason=reason,
        confidence=confidence,
        fp_categories=categories,
        vulnerability_relevance=relevance,
    )


def classify_false_positive(
    finding: GliderFinding,
    vulnerability_description: str,
) -> list[str]:
    source = finding.sol_function or ""
    categories: list[str] = []
    if not source.strip():
        categories.append("empty_function_source")
        return categories

    if _requires_state_transition(vulnerability_description) and _is_view_or_pure(source):
        categories.append("view_or_pure_for_state_transition_vulnerability")
    if _only_delegates(source):
        categories.append("delegate_only")
    if _is_placeholder(source):
        categories.append("placeholder_or_stub")
    if _has_no_behavioral_signal(source):
        categories.append("no_arithmetic_calls_or_state_writes")
    if not _has_keyword_relation(source, vulnerability_description):
        categories.append("no_meaningful_keyword_relation")
    if not _has_relevant_identifier(source, vulnerability_description):
        categories.append("no_relevant_identifiers")
    return categories


def vulnerability_keywords(description: str) -> set[str]:
    words = {
        word.lower()
        for word in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", description)
        if len(word) > 2 and word.lower() not in STOPWORDS
    }
    expanded = set(words)
    if {"health", "factor"} & words:
        expanded |= {
            "healthfactor",
            "collateral",
            "debt",
            "borrow",
            "withdraw",
            "liquidation",
            "oracle",
            "price",
            "exchange",
            "rate",
        }
    if {"share", "shares", "vault"} & words:
        expanded |= {
            "totalassets",
            "totalsupply",
            "converttoshares",
            "converttoassets",
            "deposit",
            "withdraw",
            "redeem",
            "previewdeposit",
            "previewwithdraw",
        }
    if {"amm", "invariant", "swap"} & words:
        expanded |= {"reserve", "reserves", "swap", "k", "invariant", "liquidity", "fee"}
    return expanded


def _requires_state_transition(description: str) -> bool:
    lowered = description.lower()
    return any(term in lowered for term in STATE_TRANSITION_TERMS)


def _is_view_or_pure(source: str) -> bool:
    signature = source.split("{", 1)[0].lower()
    return bool(re.search(r"\b(view|pure)\b", signature))


def _only_delegates(source: str) -> bool:
    body = _body(source)
    body_without_comments = re.sub(r"//.*|/\*.*?\*/", "", body, flags=re.S).strip()
    return bool(re.fullmatch(r"_?delegate\s*\([^;]*\)\s*;?", body_without_comments))


def _is_placeholder(source: str) -> bool:
    body = _body(source).strip().lower()
    compact = re.sub(r"\s+", "", body)
    return (
        compact in {"", ";", "{}", "revert();", "return;", "todo();"}
        or "todo" in body
        or "not implemented" in body
        or "placeholder" in body
    )


def _has_no_behavioral_signal(source: str) -> bool:
    body = _body(source)
    has_arithmetic = bool(re.search(r"(?<![=!<>])[-+*/%](?!=)|\b(add|sub|mul|div|mod)\s*\(", body))
    has_call = bool(re.search(r"(?:\.[A-Za-z_][A-Za-z0-9_]*|_[A-Za-z_][A-Za-z0-9_]*)\s*\(", body))
    has_state_write = bool(re.search(r"(?<![=!<>])=(?!=)|\+\+|--|\+=|-=|\*=|/=", body))
    return not (has_arithmetic or has_call or has_state_write)


def _has_keyword_relation(source: str, description: str) -> bool:
    haystack = _normalize_identifier_text(source)
    return any(keyword in haystack for keyword in vulnerability_keywords(description))


def _has_relevant_identifier(source: str, description: str) -> bool:
    identifiers = {token.lower() for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", source)}
    normalized = {_normalize_identifier_text(token) for token in identifiers}
    return bool(normalized & vulnerability_keywords(description))


def _body(source: str) -> str:
    if "{" not in source or "}" not in source:
        return ""
    return source[source.find("{") + 1 : source.rfind("}")]


def _normalize_identifier_text(value: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", value.lower())


def _has_hard_reject(categories: list[str]) -> bool:
    hard = {
        "empty_function_source",
        "view_or_pure_for_state_transition_vulnerability",
        "delegate_only",
        "placeholder_or_stub",
        "no_arithmetic_calls_or_state_writes",
    }
    return any(category in hard for category in categories)

