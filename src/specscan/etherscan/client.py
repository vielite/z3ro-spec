from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from specscan.schemas import EtherscanSourceBundle


class EtherscanError(RuntimeError):
    pass


class EtherscanClient:
    def __init__(
        self,
        api_key: str,
        chain_id: str = "1",
        cache_dir: str | Path | None = None,
        client: httpx.Client | None = None,
        base_url: str = "https://api.etherscan.io/v2/api",
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.api_key = api_key
        self.chain_id = chain_id
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(max_retries, 0)
        self.logger = logger
        self.client = client or httpx.Client(timeout=httpx.Timeout(timeout_seconds))
        self.base_url = base_url
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_source_bundle(self, address: str) -> EtherscanSourceBundle:
        normalized = address.lower()
        cached = self._read_cache(normalized)
        if cached:
            self._log(f"Etherscan cache hit for {normalized}")
            return cached

        self._log(f"Etherscan fetching verified source for {normalized}")
        metadata = self._get_source_metadata(normalized)
        bundle = self._bundle_from_metadata(normalized, metadata)
        if bundle.proxy and bundle.implementation:
            self._log(
                f"Etherscan proxy detected for {normalized}; "
                f"fetching implementation {bundle.implementation}"
            )
            try:
                implementation_meta = self._get_source_metadata(bundle.implementation)
                implementation_bundle = self._bundle_from_metadata(
                    bundle.implementation,
                    implementation_meta,
                )
                bundle.source_code = implementation_bundle.source_code
                bundle.abi = implementation_bundle.abi or bundle.abi
                bundle.contract_name = implementation_bundle.contract_name or bundle.contract_name
                bundle.compiler_version = (
                    implementation_bundle.compiler_version or bundle.compiler_version
                )
            except EtherscanError as exc:
                self._log(f"Etherscan implementation fetch failed: {exc}")
        self._write_cache(normalized, bundle)
        self._log(f"Etherscan source ready for {normalized} ({len(bundle.source_code)} bytes)")
        return bundle

    def _get_source_metadata(self, address: str) -> dict[str, Any]:
        payload = self._request(
            {
                "chainid": self.chain_id,
                "module": "contract",
                "action": "getsourcecode",
                "address": address,
                "apikey": self.api_key,
            }
        )
        result = payload.get("result")
        if not isinstance(result, list) or not result:
            raise EtherscanError(f"Etherscan returned no source metadata for {address}")
        metadata = result[0]
        if not isinstance(metadata, dict):
            raise EtherscanError(f"Etherscan returned malformed source metadata for {address}")
        if not str(metadata.get("SourceCode") or "").strip():
            raise EtherscanError(f"Contract {address} is unverified or has empty source")
        return metadata

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        response: httpx.Response | None = None
        last_error: Exception | None = None
        action = str(params.get("action") or "request")
        address = str(params.get("address") or "")
        for attempt in range(1, self.max_retries + 2):
            started = time.perf_counter()
            try:
                self._log(
                    "Etherscan request "
                    f"action={action} address={address} "
                    f"attempt={attempt}/{self.max_retries + 1} "
                    f"timeout={self.timeout_seconds:.0f}s"
                )
                response = self.client.get(self.base_url, params=params)
                response.raise_for_status()
                elapsed = time.perf_counter() - started
                self._log(
                    f"Etherscan response action={action} address={address} "
                    f"elapsed={elapsed:.1f}s"
                )
                break
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                elapsed = time.perf_counter() - started
                self._log(
                    f"Etherscan request failed action={action} address={address} "
                    f"attempt={attempt} elapsed={elapsed:.1f}s: {exc}"
                )
                if attempt > self.max_retries:
                    raise EtherscanError(
                        f"Etherscan request failed for {address} after "
                        f"{attempt} attempt(s): {exc}"
                    ) from exc
        if response is None:
            raise EtherscanError(f"Etherscan request failed: {last_error}")
        payload = response.json()
        if payload.get("status") == "0" and "NOTOK" in str(payload.get("message", "")):
            raise EtherscanError(str(payload.get("result") or payload.get("message")))
        return payload

    def _bundle_from_metadata(
        self,
        address: str,
        metadata: dict[str, Any],
    ) -> EtherscanSourceBundle:
        abi = metadata.get("ABI")
        parsed_abi: list[Any] | str | None = None
        if abi and abi != "Contract source code not verified":
            try:
                parsed_abi = json.loads(abi)
            except json.JSONDecodeError:
                parsed_abi = abi
        return EtherscanSourceBundle(
            address=address,
            contract_name=metadata.get("ContractName"),
            source_code=normalize_source_code(str(metadata.get("SourceCode") or "")),
            abi=parsed_abi,
            compiler_version=metadata.get("CompilerVersion"),
            proxy=str(metadata.get("Proxy") or "0") == "1",
            implementation=metadata.get("Implementation") or None,
        )

    def _read_cache(self, address: str) -> EtherscanSourceBundle | None:
        if not self.cache_dir:
            return None
        path = self.cache_dir / f"{address}.json"
        if not path.exists():
            return None
        return EtherscanSourceBundle.model_validate_json(path.read_text())

    def _write_cache(self, address: str, bundle: EtherscanSourceBundle) -> None:
        if not self.cache_dir:
            return
        path = self.cache_dir / f"{address}.json"
        path.write_text(bundle.model_dump_json(indent=2))

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger(message)


def normalize_source_code(source_code: str) -> str:
    text = source_code.strip()
    if not text:
        return ""
    if text.startswith("{{") and text.endswith("}}"):
        text = text[1:-1]
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return source_code
        sources = parsed.get("sources") if isinstance(parsed, dict) else None
        if isinstance(sources, dict):
            parts = []
            for name, item in sources.items():
                content = item.get("content") if isinstance(item, dict) else None
                if content:
                    parts.append(f"// File: {name}\n{content}")
            if parts:
                return "\n\n".join(parts)
    return source_code
