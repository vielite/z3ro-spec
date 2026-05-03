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

PARTIAL_LIQUIDATION_CLASS_TERMS = {
    "partial liquidation",
    "partial liquidations",
    "bad debt",
    "liquidation threshold",
    "liquidation_threshold",
    "liquidation bonus",
    "liquidation_bonus",
    "close factor",
    "close_factor",
    "health factor",
    "health_factor",
}

LIQUIDATION_TERMS = {
    "liquidate",
    "liquidation",
    "seize",
    "repay",
    "repayborrow",
    "debt",
    "collateral",
    "healthfactor",
    "health_factor",
}

PARTIAL_LIQUIDATION_TERMS = {
    "closefactor",
    "close_factor",
    "debt_to_cover",
    "debttocover",
    "repayamount",
    "repay_amount",
    "maxrepay",
    "max_repay",
    "partial",
    "percent",
    "percentage",
    "bps",
    "basispoints",
    "basis_points",
    "min",
    "wadmul",
    "raymul",
}

FULL_ONLY_LIQUIDATION_PATTERNS = (
    r"\b(?:repay_amount|repayamount|debt_to_cover|debttocover|amount)\s*=\s*(?:total_?debt|debt|borrow_?balance)",
    r"\b(?:close_factor|closefactor)\s*=\s*(?:1e18|10000|100_00|100|wad)",
    r"\b(?:seizeallcollateral|seize_all_collateral|seizeall|allcollateral|all_collateral)\b",
    r"\bfull\s+liquidation\b",
)

UNRELATED_LIQUIDATION_TERMS = {
    "auction",
    "bid",
    "nft",
    "idle",
    "sale",
    "vest",
    "vesting",
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
    partial_category = _partial_liquidation_category(source, vulnerability_description)
    if partial_category:
        categories.append(partial_category)
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
    if _is_partial_liquidation_vulnerability(description):
        expanded |= LIQUIDATION_TERMS | PARTIAL_LIQUIDATION_TERMS | {
            "lt",
            "bonus",
            "liquidationbonus",
            "liquidationthreshold",
            "borrower",
            "account",
            "position",
        }
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


def _partial_liquidation_category(source: str, description: str) -> str | None:
    if not _is_partial_liquidation_vulnerability(description):
        return None

    normalized_source = _normalize_identifier_text(source)
    lowered_source = source.lower()
    has_liquidation_signal = any(term in normalized_source for term in LIQUIDATION_TERMS)
    has_partial_signal = any(term in normalized_source for term in PARTIAL_LIQUIDATION_TERMS)
    has_repay_argument = bool(
        re.search(
            r"function\s+\w+\s*\([^)]*(?:repay|debt|amount|cover)[A-Za-z0-9_]*\s*[,)]",
            lowered_source,
            flags=re.S,
        )
    )
    has_close_factor_math = bool(
        re.search(
            r"\b(?:debt|borrow|repay)[A-Za-z0-9_]*\s*[*]\s*[A-Za-z0-9_]*(?:factor|bps|percent)",
            lowered_source,
        )
    )

    if not has_liquidation_signal:
        return "not_liquidation_mechanism"
    if any(term in normalized_source for term in UNRELATED_LIQUIDATION_TERMS):
        return "unrelated_liquidation_domain"
    if (
        ("reward" in normalized_source or "rewards" in normalized_source)
        and "liquidatorreward" not in normalized_source
        and not any(term in normalized_source for term in ("repaiddebt", "debt", "collateral"))
    ):
        return "unrelated_liquidation_domain"
    if any(re.search(pattern, lowered_source) for pattern in FULL_ONLY_LIQUIDATION_PATTERNS):
        return "full_liquidation_only"
    if any(re.search(pattern, normalized_source) for pattern in FULL_ONLY_LIQUIDATION_PATTERNS):
        return "full_liquidation_only"
    if has_partial_signal or has_repay_argument or has_close_factor_math:
        return None
    return "missing_partial_liquidation_mechanics"


def _is_partial_liquidation_vulnerability(description: str) -> bool:
    lowered = description.lower()
    normalized = _normalize_identifier_text(description)
    if any(term in lowered for term in PARTIAL_LIQUIDATION_CLASS_TERMS):
        return True
    return (
        "liquidation" in normalized
        and "baddebt" in normalized
        and ("bonus" in normalized or "threshold" in normalized or "closefactor" in normalized)
    )


def _has_hard_reject(categories: list[str]) -> bool:
    hard = {
        "empty_function_source",
        "view_or_pure_for_state_transition_vulnerability",
        "delegate_only",
        "placeholder_or_stub",
        "no_arithmetic_calls_or_state_writes",
        "not_liquidation_mechanism",
        "unrelated_liquidation_domain",
        "full_liquidation_only",
        "missing_partial_liquidation_mechanics",
    }
    return any(category in hard for category in categories)
