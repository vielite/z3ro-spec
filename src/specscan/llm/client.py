from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError


class LLMError(RuntimeError):
    pass


class OpenAICompatibleClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        client: httpx.Client | None = None,
        timeout_seconds: float = 180.0,
        max_retries: int = 2,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(max_retries, 0)
        self.logger = logger
        self.client = client or httpx.Client(timeout=httpx.Timeout(timeout_seconds))

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: type[BaseModel],
    ) -> BaseModel:
        last_error: Exception | None = None
        prompt = user_prompt
        for attempt in range(1, 3):
            self._log(f"LLM JSON attempt {attempt}/2 for model {self.model}")
            content = self._chat(system_prompt, prompt)
            try:
                data = _extract_json(content)
                self._log(f"LLM JSON parsed successfully for model {self.model}")
                return schema.model_validate(data)
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
                last_error = exc
                self._log(f"LLM JSON validation failed for model {self.model}: {exc}")
                prompt = (
                    user_prompt
                    + "\n\nYour previous response was malformed. Return only strict JSON "
                    "matching the requested schema. Do not include Markdown."
                )
        raise LLMError(f"LLM returned malformed JSON after retry: {last_error}")

    def _chat(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        response: httpx.Response | None = None
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            started = time.perf_counter()
            try:
                self._log(
                    "LLM request "
                    f"attempt {attempt}/{self.max_retries + 1} "
                    f"model={self.model} timeout={self.timeout_seconds:.0f}s"
                )
                response = self.client.post(
                    url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                elapsed = time.perf_counter() - started
                self._log(f"LLM response received model={self.model} elapsed={elapsed:.1f}s")
                break
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                elapsed = time.perf_counter() - started
                self._log(
                    "LLM request failed "
                    f"model={self.model} attempt={attempt} elapsed={elapsed:.1f}s: {exc}"
                )
                if attempt > self.max_retries:
                    raise LLMError(
                        f"LLM request failed for model {self.model} after "
                        f"{attempt} attempt(s): {exc}"
                    ) from exc
        if response is None:
            raise LLMError(f"LLM request failed for model {self.model}: {last_error}")
        payload = response.json()
        try:
            return str(payload["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM response did not contain choices[0].message.content") from exc

    def _log(self, message: str) -> None:
        if self.logger:
            self.logger(message)


def _extract_json(content: str) -> Any:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        stripped = stripped.removeprefix("json").strip()
    return json.loads(stripped)
