"""Environment-configured LLM gateway smoke adapter."""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from awr.domain import WorkItem


@dataclass(slots=True)
class LLMGatewayAgent:
    """Tiny HTTP gateway adapter for smoke testing external execution."""

    endpoint: str | None = None
    api_key: str | None = None

    def __post_init__(self) -> None:
        self.endpoint = self.endpoint or os.getenv("AWR_LLM_GATEWAY_URL")
        self.api_key = self.api_key or os.getenv("AWR_LLM_GATEWAY_API_KEY")

    def execute(self, work_item: WorkItem) -> str:
        prompt = work_item.description or work_item.title
        if not self.endpoint:
            return f"LLM gateway not configured; smoke prompt: {prompt}"
        request = urllib.request.Request(
            self.endpoint,
            data=prompt.encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except urllib.error.URLError as error:
            raise RuntimeError(f"LLM gateway request failed: {error}") from error

    def _headers(self) -> dict[str, str]:
        headers = {"content-type": "text/plain; charset=utf-8"}
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"
        return headers
