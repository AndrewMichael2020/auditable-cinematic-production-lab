from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from urllib.parse import urlsplit

from .errors import ProviderError, UnknownBillingStatus

TOKEN_PATTERN = re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+")


def redact(value: str) -> str:
    return TOKEN_PATTERN.sub(r"\1[REDACTED]", value)


@dataclass(frozen=True)
class ProviderResult:
    provider_request_id: str | None
    cost: Decimal
    output_url: str
    raw: dict[str, Any]


Transport = Callable[[urllib.request.Request, float], tuple[int | None, bytes, dict[str, str]]]


def default_transport(request: urllib.request.Request, timeout: float) -> tuple[int | None, bytes, dict[str, str]]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers)

class DeepInfraClient:
    def __init__(self, token: str, transport: Transport = default_transport,
                 base_url: str = "https://api.deepinfra.com/v1/inference"):
        if not token.strip():
            raise ProviderError("DEEPINFRA_TOKEN is required for a live request")
        self._token = token
        self.transport = transport
        self.base_url = base_url.rstrip("/")

    def infer(self, model: str, payload: dict[str, Any], *, timeout: float = 300) -> ProviderResult:
        return self._infer(model, payload, ("video_url", "output_url", "video"), timeout)

    def infer_audio(self, model: str, payload: dict[str, Any], *, timeout: float = 300) -> ProviderResult:
        result = self._infer(model, payload, ("audio", "audio_url", "output_url"), timeout)
        output = result.output_url
        if not urlsplit(output).scheme:
            output_format = str(payload.get("response_format", "wav"))
            output = f"data:audio/{output_format};base64,{output}"
            result = ProviderResult(result.provider_request_id, result.cost, output, result.raw)
        return result

    def _infer(self, model: str, payload: dict[str, Any], output_fields: tuple[str, ...],
               timeout: float) -> ProviderResult:
        data = json.dumps(payload, separators=(",", ":")).encode()
        auth = f"Bearer {self._token}"
        request = urllib.request.Request(
            f"{self.base_url}/{model}", data=data, method="POST",
            headers={"Authorization": auth, "Content-Type": "application/json"})
        try:
            status, body, headers = self.transport(request, timeout)
        except (TimeoutError, urllib.error.URLError) as exc:
            raise UnknownBillingStatus("provider status unknown; do not retry automatically") from exc
        if status is None or not 200 <= status < 300:
            raise ProviderError(f"provider returned HTTP {status}")
        try:
            parsed = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProviderError("provider returned invalid JSON") from exc
        inference = parsed.get("inference_status") or {}
        if "cost" not in inference:
            raise UnknownBillingStatus("provider response omitted inference_status.cost")
        try:
            cost = Decimal(str(inference["cost"]))
        except InvalidOperation as exc:
            raise UnknownBillingStatus("provider returned invalid cost") from exc
        output = next((parsed.get(field) for field in output_fields if parsed.get(field)), None)
        if not output and isinstance(parsed.get("videos"), list) and parsed["videos"]:
            output = parsed["videos"][0].get("url")
        if not output:
            raise ProviderError("provider response omitted media output")
        if not isinstance(output, str):
            raise ProviderError("provider returned invalid media output")
        return ProviderResult(headers.get("x-request-id") or parsed.get("request_id"), cost, output, parsed)

    def download(self, url: str, destination: str, *, timeout: float = 300) -> str:
        """Download an output atomically and return its SHA-256 hash."""
        from pathlib import Path

        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".partial")
        request = urllib.request.Request(url, method="GET")
        try:
            status, body, _ = self.transport(request, timeout)
        except (TimeoutError, urllib.error.URLError) as exc:
            raise ProviderError("output download failed") from exc
        scheme = urlsplit(url).scheme.lower()
        if status is None and scheme != "data":
            raise ProviderError("output download returned no HTTP status")
        if status is not None and not 200 <= status < 300:
            raise ProviderError(f"output download returned HTTP {status}")
        if not body:
            raise ProviderError("output download returned an empty body")
        partial.write_bytes(body)
        partial.replace(target)
        return hashlib.sha256(body).hexdigest()


def prompt_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()
