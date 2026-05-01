from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_KEYS = {
    "ETHERSCAN_API_KEY",
    "ETHERSCAN_CHAIN_ID",
    "TRIAGE_LLM_API_KEY",
    "TRIAGE_LLM_BASE_URL",
    "TRIAGE_LLM_MODEL",
    "FORMAL_VERIFIER_LLM_API_KEY",
    "FORMAL_VERIFIER_LLM_BASE_URL",
    "FORMAL_VERIFIER_LLM_MODEL",
    "Z3RO_SPEC_LLM_TIMEOUT_SECONDS",
    "Z3RO_SPEC_ETHERSCAN_TIMEOUT_SECONDS",
    "Z3RO_SPEC_NETWORK_RETRIES",
    "SPECSCAN_LLM_TIMEOUT_SECONDS",
    "SPECSCAN_ETHERSCAN_TIMEOUT_SECONDS",
    "SPECSCAN_NETWORK_RETRIES",
}


@dataclass(frozen=True)
class Settings:
    etherscan_api_key: str | None = None
    etherscan_chain_id: str = "1"
    triage_llm_api_key: str | None = None
    triage_llm_base_url: str | None = None
    triage_llm_model: str | None = None
    formal_verifier_llm_api_key: str | None = None
    formal_verifier_llm_base_url: str | None = None
    formal_verifier_llm_model: str | None = None
    llm_timeout_seconds: float = 300.0
    etherscan_timeout_seconds: float = 60.0
    network_retries: int = 2

    @classmethod
    def from_env(cls) -> Settings:
        env_file = _load_dotenv()
        return cls(
            etherscan_api_key=_setting("ETHERSCAN_API_KEY", env_file),
            etherscan_chain_id=_setting("ETHERSCAN_CHAIN_ID", env_file) or "1",
            triage_llm_api_key=_setting("TRIAGE_LLM_API_KEY", env_file),
            triage_llm_base_url=_setting("TRIAGE_LLM_BASE_URL", env_file),
            triage_llm_model=_setting("TRIAGE_LLM_MODEL", env_file),
            formal_verifier_llm_api_key=_setting("FORMAL_VERIFIER_LLM_API_KEY", env_file),
            formal_verifier_llm_base_url=_setting(
                "FORMAL_VERIFIER_LLM_BASE_URL",
                env_file,
            ),
            formal_verifier_llm_model=_setting("FORMAL_VERIFIER_LLM_MODEL", env_file),
            llm_timeout_seconds=_float_setting(
                "Z3RO_SPEC_LLM_TIMEOUT_SECONDS",
                env_file,
                default=300.0,
                fallback_key="SPECSCAN_LLM_TIMEOUT_SECONDS",
            ),
            etherscan_timeout_seconds=_float_setting(
                "Z3RO_SPEC_ETHERSCAN_TIMEOUT_SECONDS",
                env_file,
                default=60.0,
                fallback_key="SPECSCAN_ETHERSCAN_TIMEOUT_SECONDS",
            ),
            network_retries=_int_setting(
                "Z3RO_SPEC_NETWORK_RETRIES",
                env_file,
                default=2,
                fallback_key="SPECSCAN_NETWORK_RETRIES",
            ),
        )


def _setting(key: str, env_file: dict[str, str]) -> str | None:
    return os.getenv(key) or env_file.get(key)


def _float_setting(
    key: str,
    env_file: dict[str, str],
    *,
    default: float,
    fallback_key: str | None = None,
) -> float:
    value = _setting(key, env_file) or (
        _setting(fallback_key, env_file) if fallback_key else None
    )
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _int_setting(
    key: str,
    env_file: dict[str, str],
    *,
    default: int,
    fallback_key: str | None = None,
) -> int:
    value = _setting(key, env_file) or (
        _setting(fallback_key, env_file) if fallback_key else None
    )
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _load_dotenv() -> dict[str, str]:
    path = _find_dotenv()
    if path is None:
        return {}
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key not in ENV_KEYS:
            continue
        values[key] = _strip_quotes(value.strip())
    return values


def _find_dotenv() -> Path | None:
    candidates = [Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env"]
    for path in candidates:
        if path.exists():
            return path
    return None


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
