from __future__ import annotations

import base64
import binascii
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode

from .errors import ProviderError, UnknownBillingStatus
from .provider import Transport, default_transport


@dataclass(frozen=True)
class ElevenLabsDialogueResult:
    provider_request_id: str
    character_cost: int
    audio: bytes
    voice_segments: list[dict[str, Any]]
    alignment: dict[str, Any] | None
    normalized_alignment: dict[str, Any] | None


@dataclass(frozen=True)
class ElevenLabsSpeechResult:
    provider_request_id: str
    character_cost: int
    audio: bytes
    alignment: dict[str, Any] | None
    normalized_alignment: dict[str, Any] | None


@dataclass(frozen=True)
class ElevenLabsSoundEffectResult:
    provider_request_id: str
    character_cost: int
    audio: bytes
    content_type: str


class ElevenLabsClient:
    def __init__(
        self,
        api_key: str,
        transport: Transport = default_transport,
        base_url: str = "https://api.elevenlabs.io",
    ):
        if not api_key.strip():
            raise ProviderError("ELEVENLABS_KEY is required for an ElevenLabs request")
        self._api_key = api_key
        self.transport = transport
        self.base_url = base_url.rstrip("/")

    def _request_json(
        self, request: urllib.request.Request, *, timeout: float
    ) -> tuple[dict[str, Any], dict[str, str]]:
        try:
            status, body, headers = self.transport(request, timeout)
        except (TimeoutError, urllib.error.URLError) as exc:
            raise UnknownBillingStatus(
                "ElevenLabs request status is unknown; do not retry automatically"
            ) from exc
        if status is None or not 200 <= status < 300:
            raise ProviderError(f"ElevenLabs returned HTTP {status}")
        try:
            parsed = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProviderError("ElevenLabs returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise ProviderError("ElevenLabs returned an invalid response object")
        return parsed, {str(key).lower(): str(value) for key, value in headers.items()}

    def list_voices(self, *, timeout: float = 60) -> list[dict[str, Any]]:
        request = urllib.request.Request(
            f"{self.base_url}/v1/voices",
            method="GET",
            headers={"xi-api-key": self._api_key},
        )
        parsed, _ = self._request_json(request, timeout=timeout)
        voices = parsed.get("voices")
        if not isinstance(voices, list):
            raise ProviderError("ElevenLabs voice catalog is missing voices")
        return [item for item in voices if isinstance(item, dict)]

    def text_to_dialogue(
        self,
        inputs: list[dict[str, str]],
        *,
        model_id: str = "eleven_v3",
        language_code: str = "en",
        seed: int = 0,
        output_format: str = "wav_24000",
        apply_text_normalization: str = "auto",
        timeout: float = 300,
    ) -> ElevenLabsDialogueResult:
        payload = {
            "inputs": inputs,
            "model_id": model_id,
            "language_code": language_code,
            "seed": seed,
            "apply_text_normalization": apply_text_normalization,
        }
        endpoint = (
            f"{self.base_url}/v1/text-to-dialogue/with-timestamps?"
            + urlencode({"output_format": output_format})
        )
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, separators=(",", ":")).encode(),
            method="POST",
            headers={
                "xi-api-key": self._api_key,
                "Content-Type": "application/json",
            },
        )
        parsed, headers = self._request_json(request, timeout=timeout)
        encoded = parsed.get("audio_base64")
        if not isinstance(encoded, str) or not encoded:
            raise ProviderError("ElevenLabs response omitted dialogue audio")
        try:
            audio = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ProviderError("ElevenLabs returned invalid audio encoding") from exc
        if not audio:
            raise ProviderError("ElevenLabs returned empty dialogue audio")
        request_id = headers.get("request-id") or headers.get("x-request-id")
        cost_text = headers.get("character-cost")
        try:
            character_cost = int(str(cost_text))
        except (TypeError, ValueError) as exc:
            raise UnknownBillingStatus(
                "ElevenLabs response omitted a valid character-cost header"
            ) from exc
        if not request_id or character_cost < 0:
            raise UnknownBillingStatus(
                "ElevenLabs response omitted request or usage provenance"
            )
        segments = parsed.get("voice_segments")
        if not isinstance(segments, list):
            raise ProviderError("ElevenLabs response omitted voice segments")
        return ElevenLabsDialogueResult(
            provider_request_id=request_id,
            character_cost=character_cost,
            audio=audio,
            voice_segments=[item for item in segments if isinstance(item, dict)],
            alignment=(parsed.get("alignment")
                       if isinstance(parsed.get("alignment"), dict) else None),
            normalized_alignment=(
                parsed.get("normalized_alignment")
                if isinstance(parsed.get("normalized_alignment"), dict) else None
            ),
        )

    @staticmethod
    def _provenance(headers: dict[str, str]) -> tuple[str, int]:
        request_id = headers.get("request-id") or headers.get("x-request-id")
        cost_text = headers.get("character-cost")
        try:
            character_cost = int(str(cost_text))
        except (TypeError, ValueError) as exc:
            raise UnknownBillingStatus(
                "ElevenLabs response omitted a valid character-cost header"
            ) from exc
        if not request_id or character_cost < 0:
            raise UnknownBillingStatus(
                "ElevenLabs response omitted request or usage provenance"
            )
        return request_id, character_cost

    def text_to_speech(
        self,
        text: str,
        voice_id: str,
        *,
        model_id: str = "eleven_v3",
        language_code: str = "en",
        seed: int = 0,
        output_format: str = "wav_24000",
        apply_text_normalization: str = "auto",
        timeout: float = 300,
    ) -> ElevenLabsSpeechResult:
        """Generate one isolated persona line with timestamped alignment evidence."""
        if not text.strip() or not voice_id.strip():
            raise ProviderError("ElevenLabs speech requires text and voice_id")
        payload = {
            "text": text,
            "model_id": model_id,
            "language_code": language_code,
            "seed": seed,
            "apply_text_normalization": apply_text_normalization,
        }
        endpoint = (
            f"{self.base_url}/v1/text-to-speech/{quote(voice_id, safe='')}/with-timestamps?"
            + urlencode({"output_format": output_format})
        )
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, separators=(",", ":")).encode(),
            method="POST",
            headers={
                "xi-api-key": self._api_key,
                "Content-Type": "application/json",
            },
        )
        parsed, headers = self._request_json(request, timeout=timeout)
        encoded = parsed.get("audio_base64")
        if not isinstance(encoded, str) or not encoded:
            raise ProviderError("ElevenLabs response omitted speech audio")
        try:
            audio = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ProviderError("ElevenLabs returned invalid speech audio") from exc
        request_id, character_cost = self._provenance(headers)
        return ElevenLabsSpeechResult(
            provider_request_id=request_id,
            character_cost=character_cost,
            audio=audio,
            alignment=(parsed.get("alignment")
                       if isinstance(parsed.get("alignment"), dict) else None),
            normalized_alignment=(
                parsed.get("normalized_alignment")
                if isinstance(parsed.get("normalized_alignment"), dict) else None
            ),
        )

    def sound_effect(
        self,
        text: str,
        *,
        duration_seconds: float | None = None,
        loop: bool = False,
        prompt_influence: float = 0.3,
        model_id: str = "eleven_text_to_sound_v2",
        output_format: str = "mp3_44100_192",
        timeout: float = 300,
    ) -> ElevenLabsSoundEffectResult:
        """Generate a bounded ambience or sound-effect asset with usage provenance."""
        if not text.strip():
            raise ProviderError("ElevenLabs sound effect requires text")
        if duration_seconds is not None and not 0.5 <= duration_seconds <= 30:
            raise ProviderError("ElevenLabs sound-effect duration must be 0.5 to 30 seconds")
        if not 0 <= prompt_influence <= 1:
            raise ProviderError("ElevenLabs prompt influence must be between 0 and 1")
        payload: dict[str, Any] = {
            "text": text,
            "loop": loop,
            "prompt_influence": prompt_influence,
            "model_id": model_id,
        }
        if duration_seconds is not None:
            payload["duration_seconds"] = duration_seconds
        endpoint = f"{self.base_url}/v1/sound-generation?" + urlencode({
            "output_format": output_format
        })
        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload, separators=(",", ":")).encode(),
            method="POST",
            headers={
                "xi-api-key": self._api_key,
                "Content-Type": "application/json",
            },
        )
        try:
            status, body, raw_headers = self.transport(request, timeout)
        except (TimeoutError, urllib.error.URLError) as exc:
            raise UnknownBillingStatus(
                "ElevenLabs sound-effect status is unknown; do not retry automatically"
            ) from exc
        if status is None or not 200 <= status < 300:
            raise ProviderError(f"ElevenLabs returned HTTP {status}")
        if not body:
            raise ProviderError("ElevenLabs returned empty sound-effect audio")
        headers = {str(key).lower(): str(value) for key, value in raw_headers.items()}
        request_id, character_cost = self._provenance(headers)
        return ElevenLabsSoundEffectResult(
            provider_request_id=request_id,
            character_cost=character_cost,
            audio=body,
            content_type=headers.get("content-type", "audio/mpeg"),
        )
