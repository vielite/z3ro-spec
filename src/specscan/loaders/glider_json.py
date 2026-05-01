from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from specscan.analysis.prioritizer import normalize_value
from specscan.schemas import GliderFinding

WRAPPER_KEYS = ("findings", "results", "data", "candidates", "matches")


def load_glider_json(path: str | Path) -> list[GliderFinding]:
    raw = json.loads(Path(path).read_text())
    records = _extract_records(raw)
    return [_coerce_finding(record) for record in records]


def _extract_records(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        for key in WRAPPER_KEYS:
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if {"contract", "sol_function"}.issubset(raw):
            return [raw]
    raise ValueError("Unsupported Glider JSON shape: expected list or known wrapper key")


def _coerce_finding(record: dict[str, Any]) -> GliderFinding:
    known = {
        "contract",
        "contract_name",
        "sol_function",
        "sol_function_source_lines",
        "value",
    }
    raw_value = record.get("value")
    normalized_value, value_status = normalize_value(raw_value)
    value = normalized_value if value_status in {"valid", "zero_or_negative"} else None
    return GliderFinding(
        contract=str(record.get("contract") or record.get("address") or ""),
        contract_name=record.get("contract_name") or record.get("name"),
        sol_function=str(record.get("sol_function") or record.get("function") or ""),
        sol_function_source_lines=record.get("sol_function_source_lines")
        or record.get("source_lines"),
        value=value,
        normalized_value=normalized_value,
        value_status=value_status,
        extra={key: value for key, value in record.items() if key not in known},
    )
