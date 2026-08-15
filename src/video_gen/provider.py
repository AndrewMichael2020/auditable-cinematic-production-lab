from __future__ import annotations

import hashlib
import http.client
import json
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Callable
from urllib.parse import quote, urlsplit, urlunsplit

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


@dataclass(frozen=True)
class QueuedProviderResult:
    provider_request_id: str
    raw: dict[str, Any]


Transport = Callable[[urllib.request.Request, float], tuple[int | None, bytes, dict[str, str]]]


def default_transport(request: urllib.request.Request, timeout: float) -> tuple[int | None, bytes, dict[str, str]]:
    context = None
    verify_paths = ssl.get_default_verify_paths()
    if verify_paths.cafile is None:
        # Some python.org macOS builds do not inherit the system trust bundle.
        # Prefer the host's maintained CA file without disabling verification.
        from pathlib import Path

        for candidate in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
            if Path(candidate).is_file():
                context = ssl.create_default_context(cafile=candidate)
                break
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
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

    def submit_webhook(
        self,
        model: str,
        payload: dict[str, Any],
        webhook_url: str,
        *,
        timeout: float = 60,
    ) -> QueuedProviderResult:
        """Submit long-running native inference without holding an HTTP connection open."""
        parts = urlsplit(webhook_url)
        if (
            parts.scheme != "https"
            or not parts.netloc
            or parts.username is not None
            or parts.password is not None
        ):
            raise ProviderError("DeepInfra webhook must be a public HTTPS URL")
        submitted = {**payload, "webhook": webhook_url}
        request = urllib.request.Request(
            f"{self.base_url}/{model}",
            data=json.dumps(submitted, separators=(",", ":")).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
        )
        try:
            status, body, headers = self.transport(request, timeout)
        except (TimeoutError, urllib.error.URLError, http.client.RemoteDisconnected,
                ConnectionResetError) as exc:
            raise UnknownBillingStatus(
                "provider queue status unknown; do not retry automatically"
            ) from exc
        if status is None or not 200 <= status < 300:
            raise ProviderError(f"provider returned HTTP {status}")
        try:
            parsed = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProviderError("provider returned invalid JSON") from exc
        request_id = headers.get("x-request-id") or parsed.get("request_id")
        queue_status = (parsed.get("inference_status") or {}).get("status")
        if not request_id:
            raise UnknownBillingStatus("provider queued response omitted request id")
        if queue_status != "queued":
            raise ProviderError("provider did not acknowledge webhook request as queued")
        return QueuedProviderResult(str(request_id), parsed)

    def result_from_webhook(
        self,
        payload: dict[str, Any],
        packet: dict[str, Any],
        *,
        timeout: float = 300,
    ) -> ProviderResult:
        """Normalize the documented webhook envelope into a regular media result."""
        inference = packet.get("inference_status") or {}
        status = inference.get("status")
        if status == "failed":
            raise ProviderError("DeepInfra webhook reported failed inference")
        results = packet.get("results")
        media_fields = ("video_url", "output_url", "video")
        if isinstance(results, dict):
            parsed = {
                **results,
                "request_id": packet.get("request_id"),
                "inference_status": inference,
            }
        elif any(packet.get(field) for field in media_fields) and inference.get("cost") is not None:
            # Current long-running video callbacks use the native response shape:
            # media and cost at the top level, with no explicit succeeded status.
            parsed = packet
        else:
            raise ProviderError("DeepInfra webhook omitted successful media results")
        return self._result_from_parsed(
            parsed,
            payload,
            media_fields,
            timeout,
        )

    def infer_audio(self, model: str, payload: dict[str, Any], *, timeout: float = 300,
                    version: str | None = None,
                    fallback_price_usd_per_million_characters: Decimal | None = None,
                    ) -> ProviderResult:
        result = self._infer(
            model, payload, ("audio", "audio_url", "output_url"), timeout,
            version=version,
            fallback_price_usd_per_million_characters=(
                fallback_price_usd_per_million_characters
            ),
        )
        output = result.output_url
        if not urlsplit(output).scheme:
            output_format = str(payload.get("response_format", "wav"))
            output = f"data:audio/{output_format};base64,{output}"
            result = ProviderResult(result.provider_request_id, result.cost, output, result.raw)
        return result

    def _infer(self, model: str, payload: dict[str, Any], output_fields: tuple[str, ...],
               timeout: float, *, version: str | None = None,
               fallback_price_usd_per_million_characters: Decimal | None = None,
               ) -> ProviderResult:
        data = json.dumps(payload, separators=(",", ":")).encode()
        auth = f"Bearer {self._token}"
        endpoint = f"{self.base_url}/{model}"
        if version:
            endpoint = f"{endpoint}?version={quote(version, safe='')}"
        request = urllib.request.Request(
            endpoint, data=data, method="POST",
            headers={"Authorization": auth, "Content-Type": "application/json"})
        try:
            status, body, headers = self.transport(request, timeout)
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, ssl.SSLCertVerificationError):
                raise ProviderError(
                    "local TLS certificate verification failed before request submission"
                ) from exc
            raise UnknownBillingStatus(
                "provider status unknown; do not retry automatically"
            ) from exc
        except TimeoutError as exc:
            raise UnknownBillingStatus("provider status unknown; do not retry automatically") from exc
        except (http.client.RemoteDisconnected, ConnectionResetError) as exc:
            raise UnknownBillingStatus(
                "provider status unknown after connection closed; do not retry automatically"
            ) from exc
        if status is None or not 200 <= status < 300:
            raise ProviderError(f"provider returned HTTP {status}")
        try:
            parsed = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProviderError("provider returned invalid JSON") from exc
        provider_request_id = headers.get("x-request-id") or parsed.get("request_id")
        if provider_request_id and not parsed.get("request_id"):
            parsed["request_id"] = provider_request_id
        return self._result_from_parsed(
            parsed,
            payload,
            output_fields,
            timeout,
            fallback_price_usd_per_million_characters=(
                fallback_price_usd_per_million_characters
            ),
        )

    def _result_from_parsed(
        self,
        parsed: dict[str, Any],
        payload: dict[str, Any],
        output_fields: tuple[str, ...],
        timeout: float,
        *,
        fallback_price_usd_per_million_characters: Decimal | None = None,
    ) -> ProviderResult:
        provider_request_id = parsed.get("request_id")
        inference = parsed.get("inference_status") or {}
        cost_value = inference.get("cost")
        if cost_value is None:
            if not provider_request_id:
                raise UnknownBillingStatus(
                    "provider response omitted both cost and request id"
                )
            submitted_text = payload.get("input", payload.get("text"))
            provider_characters = parsed.get("input_character_length")
            if fallback_price_usd_per_million_characters is not None:
                if (
                    not isinstance(submitted_text, str)
                    or not isinstance(provider_characters, int)
                    or provider_characters != len(submitted_text)
                    or fallback_price_usd_per_million_characters < 0
                ):
                    raise UnknownBillingStatus(
                        "provider character usage did not match the submitted audio text"
                    )
                cost = (
                    fallback_price_usd_per_million_characters
                    * provider_characters / Decimal("1000000")
                )
                parsed["_cost_source"] = (
                    "provider_input_character_length_x_verified_registry_rate"
                )
            else:
                cost = self._request_cost(str(provider_request_id), timeout=timeout)
                parsed["_cost_source"] = "request_costs_endpoint"
        else:
            try:
                cost = Decimal(str(cost_value))
            except InvalidOperation as exc:
                raise UnknownBillingStatus("provider returned invalid cost") from exc
            parsed["_cost_source"] = "inference_status.cost"
        output = next((parsed.get(field) for field in output_fields if parsed.get(field)), None)
        if not output and isinstance(parsed.get("videos"), list) and parsed["videos"]:
            output = parsed["videos"][0].get("url")
        if not output:
            raise ProviderError("provider response omitted media output")
        if not isinstance(output, str):
            raise ProviderError("provider returned invalid media output")
        return ProviderResult(str(provider_request_id) if provider_request_id else None,
                              cost, output, parsed)

    def _request_cost(self, request_id: str, *, timeout: float) -> Decimal:
        """Resolve a missing inline cost through DeepInfra's official cost API once."""
        base = urlsplit(self.base_url)
        url = urlunsplit((base.scheme, base.netloc, "/v1/request-costs", "", ""))
        request = urllib.request.Request(
            url,
            data=json.dumps({"requestIds": [request_id]}, separators=(",", ":")).encode(),
            method="POST",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
        )
        try:
            status, body, _ = self.transport(request, timeout)
        except (TimeoutError, urllib.error.URLError, http.client.RemoteDisconnected,
                ConnectionResetError) as exc:
            raise UnknownBillingStatus(
                "provider request cost could not be reconciled; do not retry automatically"
            ) from exc
        if status is None or not 200 <= status < 300:
            raise UnknownBillingStatus(
                "provider request cost endpoint did not return success"
            )
        try:
            parsed = json.loads(body)
            matches = [
                item for item in parsed.get("requests", [])
                if item.get("requestId") == request_id
            ]
            nano_usd = Decimal(str(matches[0]["costNanoUsd"]))
        except (IndexError, KeyError, TypeError, InvalidOperation,
                json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise UnknownBillingStatus(
                "provider request cost response was incomplete"
            ) from exc
        if nano_usd < 0:
            raise UnknownBillingStatus("provider request cost was negative")
        return nano_usd / Decimal("1000000000")

    def download(self, url: str, destination: str, *, timeout: float = 300) -> str:
        """Download an output atomically and return its SHA-256 hash."""
        from pathlib import Path

        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".partial")
        request = urllib.request.Request(url, method="GET")
        try:
            status, body, _ = self.transport(request, timeout)
        except (TimeoutError, urllib.error.URLError, http.client.RemoteDisconnected,
                ConnectionResetError) as exc:
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
