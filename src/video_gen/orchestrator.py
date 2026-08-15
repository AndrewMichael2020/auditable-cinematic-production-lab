from __future__ import annotations

import hashlib
import json
import os
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .config import ProjectConfig
from .elevenlabs import ElevenLabsClient
from .errors import PolicyError, ProviderError, UnknownBillingStatus
from .ledger import Ledger
from .provider import DeepInfraClient, prompt_hash
from .voice import validate_voice_realization, voice_realization_sha256

COST_COMPARISON_EPSILON = Decimal("0.000000000001")
DEFAULT_MAX_PARTNER_AVATAR_ATTEMPTS = 5
VIDEO_ROLE_COUNT_KEYS = {
    "final_video": "max_wan22_5s_finals",
    "cosmos_world_video": "max_cosmos3_super_5s_candidates",
}
PROMOTED_VIDEO_ROLES = {"final_video", "cosmos_world_video"}


def reported_cost_exceeds_reservation(reported: Decimal, reserved: Decimal) -> bool:
    """Ignore provider JSON float noise smaller than one trillionth of a dollar."""
    return reported - reserved > COST_COMPARISON_EPSILON


def audit_safe_url(url: str) -> str:
    """Keep output provenance without persisting signed query credentials."""
    parts = urlsplit(url)
    if parts.scheme.lower() == "data":
        # DeepInfra video models may inline the complete media as a Data URL.
        # Preserve the media type/encoding while excluding the payload itself.
        header = url.partition(",")[0][:128]
        return f"{header},[OMITTED]"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


@dataclass(frozen=True)
class PlannedRequest:
    request_id: str
    model: str
    reserved_usd: Decimal
    prompt_sha256: str
    dry_run: bool
    output_path: str | None = None
    output_sha256: str | None = None
    provider_request_id: str | None = None


@dataclass(frozen=True)
class DialogueCandidate:
    request_id: str
    model: str
    reserved_usd: Decimal
    input_characters: int
    dry_run: bool
    output_path: str | None = None
    output_sha256: str | None = None
    manifest_path: str | None = None
    provider_request_id: str | None = None
    character_cost: int | None = None


class Orchestrator:
    def __init__(self, config: ProjectConfig, ledger: Ledger, profile: str, *,
                 run_cap_usd: Decimal | None = None,
                 partner_avatar_attempt_cap: int = DEFAULT_MAX_PARTNER_AVATAR_ATTEMPTS):
        self.config = config
        self.ledger = ledger
        self.profile = profile
        profile_cap = config.profile_cap(profile)
        if run_cap_usd is not None and (run_cap_usd <= 0 or run_cap_usd > profile_cap):
            raise PolicyError(f"run cap must be positive and no higher than profile cap USD {profile_cap}")
        if not 1 <= partner_avatar_attempt_cap <= 20:
            raise PolicyError("partner avatar attempt cap must be between 1 and 20")
        self.cap = min(profile_cap, run_cap_usd) if run_cap_usd is not None else profile_cap
        self.explicit_run_cap = run_cap_usd is not None
        self.partner_avatar_attempt_cap = partner_avatar_attempt_cap

    def _infer_video(
        self,
        client: DeepInfraClient,
        model_id: str,
        payload: dict[str, Any],
        *,
        request_id: str,
        request_sha256: str,
        timeout: float,
        webhook_url: str | None,
        webhook_result_path: str | Path | None,
        webhook_wait_seconds: float,
    ):
        if webhook_url is None:
            return client.infer(model_id, payload, timeout=timeout)
        queued = client.submit_webhook(
            model_id,
            payload,
            webhook_url,
            timeout=min(60, timeout),
        )
        deadline = time.monotonic() + webhook_wait_seconds
        callback_path = Path(webhook_result_path)
        while not callback_path.is_file() and time.monotonic() < deadline:
            time.sleep(0.5)
        if not callback_path.is_file():
            self.ledger.append(
                request_id,
                "billing_unknown",
                metadata=json.dumps({
                    "provider_request_id": queued.provider_request_id,
                    "request_sha256": request_sha256,
                    "reason": "webhook_timeout",
                }, sort_keys=True),
            )
            raise UnknownBillingStatus(
                "provider webhook did not arrive; do not retry automatically"
            )
        callback = json.loads(callback_path.read_text(encoding="utf-8"))
        if callback.get("request_id") != queued.provider_request_id:
            self.ledger.append(
                request_id,
                "billing_unknown",
                metadata=json.dumps({
                    "provider_request_id": queued.provider_request_id,
                    "request_sha256": request_sha256,
                    "reason": "webhook_request_id_mismatch",
                }, sort_keys=True),
            )
            raise UnknownBillingStatus(
                "provider webhook request id did not match; do not retry automatically"
            )
        callback_status = (callback.get("inference_status") or {}).get("status")
        if callback_status == "failed":
            callback_cost = (callback.get("inference_status") or {}).get("cost")
            actual = Decimal(str(callback_cost)) if callback_cost is not None else None
            self.ledger.append(
                request_id,
                "failed" if actual is not None else "billing_unknown",
                actual=actual,
                metadata=json.dumps({
                    "provider_request_id": queued.provider_request_id,
                    "request_sha256": request_sha256,
                    "reason": "provider_webhook_failed",
                }, sort_keys=True),
            )
            raise ProviderError("provider webhook reported failed inference")
        return client.result_from_webhook(payload, callback, timeout=timeout)

    def _require_live_policy(self, *, live: bool, confirmed: bool) -> None:
        if not live:
            return
        if not confirmed:
            raise PolicyError("live request requires --confirm-live")
        self.config.require_current_pricing()

    def _client_for_live(
        self, *, live: bool, confirmed: bool, client: DeepInfraClient | None,
    ) -> DeepInfraClient | None:
        self._require_live_policy(live=live, confirmed=confirmed)
        if not live:
            return client
        return client or DeepInfraClient(os.environ.get("DEEPINFRA_TOKEN", ""))

    def _voice_binding(
        self, realization: dict[str, Any] | None, *, model_id: str,
        live: bool, provider_voice: str | None = None, seed: int | None = None,
    ) -> dict[str, Any] | None:
        if realization is None:
            if live:
                raise PolicyError("live voice generation requires an approved voice realization")
            return None
        binding = validate_voice_realization(realization, require_approved=live)
        if binding["provider_model_id"] != model_id:
            raise PolicyError("voice realization does not match the selected provider model")
        if provider_voice is not None and binding["provider_voice"] != provider_voice:
            raise PolicyError("request-time voice override conflicts with canonical realization")
        configured_seed = binding["immutable_settings"].get("seed")
        if seed is not None and configured_seed is not None and int(configured_seed) != seed:
            raise PolicyError("request-time seed override conflicts with canonical realization")
        return binding

    def run_video(self, role: str, prompt: str, *, seconds: int = 5, seed: int = 0,
                  image_input: str | None = None,
                  live: bool = False, confirmed: bool = False,
                  client: DeepInfraClient | None = None,
                  output_dir: str | Path = "outputs",
                  webhook_url: str | None = None,
                  webhook_result_path: str | Path | None = None,
                  webhook_wait_seconds: float = 900) -> PlannedRequest:
        if role not in VIDEO_ROLE_COUNT_KEYS:
            raise PolicyError("run_video accepts approved video roles only")
        if role in PROMOTED_VIDEO_ROLES and live and not confirmed:
            raise PolicyError("promoted generation requires explicit human promotion")
        # Validate policy, current pricing, and credentials before creating a
        # budget reservation. A local configuration error must not leave an
        # orphan paid-attempt record.
        client = self._client_for_live(live=live, confirmed=confirmed, client=client)
        if (webhook_url is None) != (webhook_result_path is None):
            raise PolicyError("webhook URL and webhook result path must be supplied together")
        if webhook_url is not None:
            if not live:
                raise PolicyError("webhook inference is available only for live requests")
            if not 30 <= webhook_wait_seconds <= 1800:
                raise PolicyError("webhook wait must be between 30 and 1800 seconds")
            callback_path = Path(webhook_result_path)
            if callback_path.exists():
                raise PolicyError("webhook result destination already exists")
        model = self.config.model(role)
        profile_data = self.config.raw["budget"]["profiles"][self.profile]
        count_key = VIDEO_ROLE_COUNT_KEYS[role]
        if self.ledger.reservation_count(model.id) >= int(profile_data[count_key]):
            raise PolicyError(f"candidate cap reached for {role}")
        configured_seconds = int(model.data["seconds"])
        if seconds != configured_seconds:
            raise PolicyError(f"{model.id} is approved for exactly {configured_seconds} seconds")
        if model.endpoint_type == "deepinfra_world_model":
            if not prompt.strip() or len(prompt) > int(model.data["max_prompt_characters"]):
                raise PolicyError(
                    f"world-model prompt must contain 1–{model.data['max_prompt_characters']} characters"
                )
            payload = {
                "prompt": prompt,
                "output_type": model.data["output_type"],
                "resolution": model.data["resolution"],
                "aspect_ratio": model.data["aspect_ratio"],
                "duration_seconds": seconds,
                "seed": seed,
            }
            if image_input is not None:
                image_parts = urlsplit(image_input)
                is_image_data = (
                    image_parts.scheme == "data" and image_input.startswith("data:image/")
                )
                is_public_https = (
                    image_parts.scheme == "https"
                    and bool(image_parts.netloc)
                    and image_parts.username is None
                    and image_parts.password is None
                )
                if not (is_image_data or is_public_https):
                    raise PolicyError(
                        "Cosmos image input must be an image Data URL or public HTTPS URL"
                    )
                payload["image_url"] = image_input
        else:
            if image_input is not None:
                raise PolicyError("image conditioning is approved only for the Cosmos world role")
            payload = {
                "prompt": prompt,
                "seconds": seconds,
                "resolution": model.data["resolution"],
                "orientation": (
                    model.data.get("orientation") or
                    ("landscape" if "landscape" in model.data.get("orientations", []) else None)
                ),
                "seed": seed,
            }
            if not payload["orientation"]:
                raise PolicyError(f"{model.id} has no approved output orientation")
            if model.data.get("negative_prompt"):
                payload["negative_prompt"] = model.data["negative_prompt"]
        reserved = model.reserve(seconds=seconds)
        request_id = str(uuid.uuid4())
        self.ledger.reserve(request_id, model.id, reserved, self.cap)
        planned = PlannedRequest(request_id, model.id, reserved, prompt_hash(payload), not live)
        if not live:
            return planned
        assert client is not None
        try:
            result = self._infer_video(
                client,
                model.id,
                payload,
                request_id=request_id,
                request_sha256=planned.prompt_sha256,
                timeout=float(model.data.get("request_timeout_seconds", 300)),
                webhook_url=webhook_url,
                webhook_result_path=webhook_result_path,
                webhook_wait_seconds=webhook_wait_seconds,
            )
        except UnknownBillingStatus:
            terminal = self.ledger.db.execute(
                "SELECT 1 FROM events WHERE request_id=? AND event!='reserved'",
                (request_id,),
            ).fetchone()
            if not terminal:
                self.ledger.append(request_id, "billing_unknown")
            raise
        except Exception:
            terminal = self.ledger.db.execute(
                "SELECT 1 FROM events WHERE request_id=? AND event!='reserved'",
                (request_id,),
            ).fetchone()
            if not terminal:
                self.ledger.append(request_id, "failed")
            raise
        if reported_cost_exceeds_reservation(result.cost, reserved):
            self.ledger.append(request_id, "billing_unknown", actual=result.cost,
                               metadata=json.dumps({
                                   "provider_request_id": result.provider_request_id,
                                   "output_url": audit_safe_url(result.output_url),
                                   "prompt_sha256": planned.prompt_sha256,
                                   "reason": "reported_cost_exceeded_reservation",
                               }, sort_keys=True))
            raise UnknownBillingStatus("reported cost exceeded approved reservation")
        destination = Path(output_dir) / f"{request_id}.mp4"
        base_metadata = {"provider_request_id": result.provider_request_id,
                         "output_url": audit_safe_url(result.output_url),
                         "output_path": str(destination),
                         "prompt_sha256": planned.prompt_sha256}
        try:
            output_sha256 = client.download(result.output_url, str(destination))
        except Exception:
            self.ledger.append(request_id, "failed", actual=result.cost,
                               metadata=json.dumps({**base_metadata, "reason": "download_failed"},
                                                   sort_keys=True))
            raise
        metadata = json.dumps({**base_metadata, "output_sha256": output_sha256}, sort_keys=True)
        self.ledger.append(request_id, "completed", actual=result.cost, metadata=metadata)
        return PlannedRequest(
            request_id,
            model.id,
            reserved,
            planned.prompt_sha256,
            False,
            output_path=str(destination),
            output_sha256=output_sha256,
            provider_request_id=result.provider_request_id,
        )

    def run_voice_audition(self, spec: dict[str, Any], *,
                           live: bool = False, confirmed: bool = False,
                           client: DeepInfraClient | None = None,
                           output_dir: str | Path = "outputs") -> PlannedRequest:
        """Generate one immutable persona audition/performance master."""
        required = {
            "character_id", "persona_version", "voice_persona_id",
            "voice_realization_id", "model_id", "model_version",
            "synthesis_settings", "script",
        }
        missing = required - spec.keys()
        if missing:
            raise PolicyError(
                f"voice audition spec missing: {', '.join(sorted(missing))}"
            )
        model = self.config.model("voice_design")
        if spec["model_id"] != model.id:
            raise PolicyError("voice audition model is not the approved voice-design model")
        if spec["model_version"] != model.data.get("model_version"):
            raise PolicyError("voice audition model version is not the approved immutable version")
        settings = spec["synthesis_settings"]
        if not isinstance(settings, dict):
            raise PolicyError("voice audition synthesis_settings must be an object")
        for field in ("voice", "instruct", "language", "response_format"):
            if not str(settings.get(field, "")).strip():
                raise PolicyError(f"voice audition synthesis_settings requires {field}")
        response_format = str(settings["response_format"])
        if response_format != model.data["allowed_response_format"]:
            raise PolicyError("voice audition must use the approved WAV response format")
        script = str(spec["script"])
        if not script.strip():
            raise PolicyError("voice audition script is required")
        if len(script) > int(model.data["max_input_characters"]):
            raise PolicyError("voice audition script exceeds the approved character limit")
        realization_id = str(spec["voice_realization_id"])
        destination = Path(output_dir) / f"{realization_id}.wav"
        if destination.exists():
            raise PolicyError(
                "voice audition destination already exists; create a new realization id"
            )
        self._require_live_policy(live=live, confirmed=confirmed)
        if live and client is None:
            client = DeepInfraClient(os.environ.get("DEEPINFRA_TOKEN", ""))
        profile_data = self.config.raw["budget"]["profiles"][self.profile]
        if self.ledger.reservation_count(model.id) >= int(
            profile_data["max_voice_auditions"]
        ):
            raise PolicyError("voice audition cap reached")
        payload = {
            "input": script,
            "voice": str(settings["voice"]),
            "instruct": str(settings["instruct"]),
            "language": str(settings["language"]),
            "response_format": response_format,
        }
        reserved = model.reserve(characters=len(script))
        request_id = str(uuid.uuid4())
        self.ledger.reserve(request_id, model.id, reserved, self.cap)
        planned = PlannedRequest(
            request_id, model.id, reserved, prompt_hash(payload), not live,
            output_path=str(destination) if live else None,
        )
        if not live:
            return planned
        assert client is not None
        try:
            result = client.infer_audio(
                model.id, payload,
                timeout=float(model.data.get("request_timeout_seconds", 300)),
                version=str(spec["model_version"]),
                fallback_price_usd_per_million_characters=Decimal(str(
                    model.data["price_usd_per_million_characters"]
                )),
            )
        except UnknownBillingStatus:
            self.ledger.append(request_id, "billing_unknown")
            raise
        except Exception:
            self.ledger.append(request_id, "failed")
            raise
        if reported_cost_exceeds_reservation(result.cost, reserved):
            self.ledger.append(
                request_id, "billing_unknown", actual=result.cost,
                metadata=json.dumps({
                    "provider_request_id": result.provider_request_id,
                    "output_url": audit_safe_url(result.output_url),
                    "request_sha256": planned.prompt_sha256,
                    "reason": "reported_cost_exceeded_reservation",
                }, sort_keys=True),
            )
            raise UnknownBillingStatus("reported cost exceeded approved reservation")
        base_metadata = {
            "provider_request_id": result.provider_request_id,
            "output_url": audit_safe_url(result.output_url),
            "output_path": str(destination),
            "request_sha256": planned.prompt_sha256,
            "script_sha256": prompt_hash({"input": script}),
            "voice_instruction_sha256": prompt_hash({
                "voice": settings["voice"], "instruct": settings["instruct"]
            }),
            "character_id": spec["character_id"],
            "persona_version": spec["persona_version"],
            "voice_persona_id": spec["voice_persona_id"],
            "voice_realization_id": realization_id,
            "model_version": spec["model_version"],
            "response_format": response_format,
            "cost_source": result.raw.get("_cost_source"),
            "provider_input_character_length": result.raw.get(
                "input_character_length"
            ),
        }
        try:
            output_sha256 = client.download(result.output_url, str(destination))
        except Exception:
            self.ledger.append(
                request_id, "failed", actual=result.cost,
                metadata=json.dumps(
                    {**base_metadata, "reason": "download_failed"}, sort_keys=True
                ),
            )
            raise
        self.ledger.append(
            request_id, "completed", actual=result.cost,
            metadata=json.dumps(
                {**base_metadata, "output_sha256": output_sha256}, sort_keys=True
            ),
        )
        return PlannedRequest(
            request_id, model.id, reserved, planned.prompt_sha256, False,
            output_path=str(destination), output_sha256=output_sha256,
            provider_request_id=result.provider_request_id,
        )

    def run_dialogue_candidate(
        self,
        spec: dict[str, Any],
        *,
        live: bool = False,
        confirmed: bool = False,
        client: ElevenLabsClient | None = None,
        output_dir: str | Path = "outputs",
    ) -> DialogueCandidate:
        """Generate one bounded, timestamped multi-speaker casting candidate."""
        required = {
            "sequence_id", "candidate_id", "model_id", "language_code",
            "output_format", "apply_text_normalization", "seed", "inputs", "turns",
        }
        missing = required - spec.keys()
        if missing:
            raise PolicyError(
                f"dialogue candidate spec missing: {', '.join(sorted(missing))}"
            )
        model = self.config.model("dialogue_voice")
        if spec["model_id"] != model.id:
            raise PolicyError("dialogue candidate is not bound to the approved model")
        inputs = spec["inputs"]
        turns = spec["turns"]
        if (
            not isinstance(inputs, list) or not inputs
            or not isinstance(turns, list) or len(turns) != len(inputs)
        ):
            raise PolicyError("dialogue candidate requires aligned inputs and turns")
        if len(inputs) > int(model.data["max_dialogue_turns"]):
            raise PolicyError("dialogue candidate exceeds the approved turn limit")
        for item in inputs:
            if (
                not isinstance(item, dict)
                or not str(item.get("text", "")).strip()
                or not str(item.get("voice_id", "")).strip()
            ):
                raise PolicyError("dialogue candidate input requires text and voice_id")
        input_characters = sum(len(str(item["text"])) for item in inputs)
        if input_characters > int(model.data["max_input_characters"]):
            raise PolicyError("dialogue candidate exceeds the approved character limit")
        if spec["output_format"] != model.data["output_format"]:
            raise PolicyError("dialogue candidate output format is not approved")
        self._require_live_policy(live=live, confirmed=confirmed)
        if live and client is None:
            client = ElevenLabsClient(os.environ.get("ELEVENLABS_KEY", ""))
        if self.ledger.reservation_count(model.id) >= int(
            self.config.raw["budget"]["profiles"][self.profile]["max_dialogue_candidates"]
        ):
            raise PolicyError("dialogue candidate cap reached")

        candidate_id = str(spec["candidate_id"])
        if not candidate_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in candidate_id):
            raise PolicyError("dialogue candidate id must be lowercase letters, digits, or hyphens")
        destination = Path(output_dir) / f"{candidate_id}.wav"
        manifest_path = Path(output_dir) / f"{candidate_id}.manifest.json"
        if destination.exists() or manifest_path.exists():
            raise PolicyError("dialogue candidate destination already exists")
        safe_request = {
            key: spec[key] for key in (
                "sequence_id", "candidate_id", "model_id", "language_code",
                "output_format", "apply_text_normalization", "seed", "inputs", "turns",
            )
        }
        request_sha256 = prompt_hash(safe_request)
        reserved = model.reserve(characters=input_characters)
        request_id = str(uuid.uuid4())
        self.ledger.reserve(request_id, model.id, reserved, self.cap)
        if not live:
            return DialogueCandidate(
                request_id=request_id,
                model=model.id,
                reserved_usd=reserved,
                input_characters=input_characters,
                dry_run=True,
            )

        assert client is not None
        try:
            result = client.text_to_dialogue(
                inputs,
                model_id=model.id,
                language_code=str(spec["language_code"]),
                seed=int(spec["seed"]),
                output_format=str(spec["output_format"]),
                apply_text_normalization=str(spec["apply_text_normalization"]),
                timeout=float(model.data.get("request_timeout_seconds", 300)),
            )
        except UnknownBillingStatus:
            self.ledger.append(request_id, "billing_unknown")
            raise
        except Exception as exc:
            self.ledger.append(
                request_id,
                "failed",
                metadata=json.dumps({
                    "reason": "provider_request_failed",
                    "error_type": type(exc).__name__,
                    "request_sha256": request_sha256,
                }, sort_keys=True),
            )
            raise

        destination.parent.mkdir(parents=True, exist_ok=True)
        audio_partial = destination.with_suffix(destination.suffix + ".partial")
        manifest_partial = manifest_path.with_suffix(manifest_path.suffix + ".partial")
        try:
            audio_partial.write_bytes(result.audio)
            audio_partial.replace(destination)
            output_sha256 = hashlib.sha256(result.audio).hexdigest()
            manifest = {
                "schema_version": "1.0",
                "artifact_type": "elevenlabs_dialogue_candidate",
                "sequence_id": spec["sequence_id"],
                "candidate_id": candidate_id,
                "model_id": model.id,
                "provider_request_id": result.provider_request_id,
                "character_cost": result.character_cost,
                "billing_unit": "elevenlabs_credits",
                "input_characters": input_characters,
                "request_sha256": request_sha256,
                "output_path": str(destination),
                "output_sha256": output_sha256,
                "turns": turns,
                "voice_segments": result.voice_segments,
                "alignment": result.alignment,
                "normalized_alignment": result.normalized_alignment,
                "human_review": {
                    "decision": "pending",
                    "note": "Casting approval selects voices; this exact performance still requires review.",
                },
            }
            manifest_partial.write_text(
                json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            manifest_partial.replace(manifest_path)
        except Exception:
            self.ledger.append(
                request_id,
                "failed",
                actual=Decimal("0"),
                metadata=json.dumps({
                    "provider_request_id": result.provider_request_id,
                    "character_cost": result.character_cost,
                    "billing_unit": "elevenlabs_credits",
                    "reason": "artifact_persistence_failed",
                    "request_sha256": request_sha256,
                }, sort_keys=True),
            )
            raise
        self.ledger.append(
            request_id,
            "completed",
            actual=Decimal("0"),
            metadata=json.dumps({
                "provider_request_id": result.provider_request_id,
                "character_cost": result.character_cost,
                "billing_unit": "elevenlabs_credits",
                "output_path": str(destination),
                "output_sha256": output_sha256,
                "manifest_path": str(manifest_path),
                "request_sha256": request_sha256,
            }, sort_keys=True),
        )
        return DialogueCandidate(
            request_id=request_id,
            model=model.id,
            reserved_usd=reserved,
            input_characters=input_characters,
            dry_run=False,
            output_path=str(destination),
            output_sha256=output_sha256,
            manifest_path=str(manifest_path),
            provider_request_id=result.provider_request_id,
            character_cost=result.character_cost,
        )

    def run_image_video(self, image_input: str, prompt: str, *, audio_input: str | None = None,
                        seconds: int = 5,
                        seed: int = 0, live: bool = False, confirmed: bool = False,
                        allow_partner: bool = False,
                        client: DeepInfraClient | None = None,
                        output_dir: str | Path = "outputs",
                        webhook_url: str | None = None,
                        webhook_result_path: str | Path | None = None,
                        webhook_wait_seconds: float = 900) -> PlannedRequest:
        """Animate one approved storyboard plate through the bounded Stage 2 I2V exception."""
        if not allow_partner:
            raise PolicyError("partner I2V model requires --allow-partner-i2v")
        image_parts = urlsplit(image_input)
        is_image_data = image_parts.scheme == "data" and image_input.startswith("data:image/")
        is_public_https = (image_parts.scheme == "https" and bool(image_parts.netloc)
                           and image_parts.username is None and image_parts.password is None)
        if not (is_image_data or is_public_https):
            raise PolicyError("I2V input must be an image Data URL or public HTTPS URL")
        if audio_input is not None:
            audio_parts = urlsplit(audio_input)
            is_audio_data = (
                audio_parts.scheme == "data" and audio_input.startswith("data:audio/")
            )
            is_public_audio_https = (
                audio_parts.scheme == "https" and bool(audio_parts.netloc)
                and audio_parts.username is None and audio_parts.password is None
            )
            if not (is_audio_data or is_public_audio_https):
                raise PolicyError("I2V audio must be an audio Data URL or public HTTPS URL")
        if not prompt.strip() or len(prompt) > 1500:
            raise PolicyError("I2V prompt must contain 1–1500 characters")
        client = self._client_for_live(live=live, confirmed=confirmed, client=client)
        if (webhook_url is None) != (webhook_result_path is None):
            raise PolicyError("webhook URL and webhook result path must be supplied together")
        if webhook_url is not None:
            if not live:
                raise PolicyError("webhook inference is available only for live requests")
            if not 30 <= webhook_wait_seconds <= 1800:
                raise PolicyError("webhook wait must be between 30 and 1800 seconds")
            if Path(webhook_result_path).exists():
                raise PolicyError("webhook result destination already exists")
        model = self.config.model("image_to_video")
        configured_seconds = int(model.data["seconds"])
        allowed_seconds = {
            int(value) for value in model.data.get("allowed_seconds", [configured_seconds])
        }
        if seconds not in allowed_seconds:
            raise PolicyError(
                f"{model.id} is approved for durations {sorted(allowed_seconds)} seconds"
            )
        profile_data = self.config.raw["budget"]["profiles"][self.profile]
        if self.ledger.reservation_count(model.id) >= int(
            profile_data["max_wan26_i2v_requests"]
        ):
            raise PolicyError("candidate cap reached for image_to_video")
        negative_prompt = str(model.data["negative_prompt"])
        if len(negative_prompt) > 500:
            raise PolicyError("configured I2V negative prompt exceeds provider limit")
        payload = {
            "img_url": image_input,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "resolution": model.data["resolution"],
            "duration": seconds,
            "prompt_extend": False,
            "shot_type": "single",
            "watermark": False,
            "seed": seed,
        }
        if audio_input is not None:
            if model.data.get("synchronized_audio_input_allowed") is not True:
                raise PolicyError("configured I2V model does not allow synchronized audio input")
            payload["audio_url"] = audio_input
        reserved = model.reserve(seconds=seconds)
        request_id = str(uuid.uuid4())
        self.ledger.reserve(request_id, model.id, reserved, self.cap)
        safe_payload = {
            key: value for key, value in payload.items()
            if key not in {"img_url", "audio_url"}
        }
        safe_payload["image_sha256"] = prompt_hash({"image": image_input})
        if audio_input is not None:
            safe_payload["audio_sha256"] = prompt_hash({"audio": audio_input})
        planned = PlannedRequest(request_id, model.id, reserved, prompt_hash(safe_payload), not live)
        if not live:
            return planned
        assert client is not None
        try:
            result = self._infer_video(
                client,
                model.id,
                payload,
                request_id=request_id,
                request_sha256=planned.prompt_sha256,
                timeout=float(model.data.get("request_timeout_seconds", 600)),
                webhook_url=webhook_url,
                webhook_result_path=webhook_result_path,
                webhook_wait_seconds=webhook_wait_seconds,
            )
        except UnknownBillingStatus:
            terminal = self.ledger.db.execute(
                "SELECT 1 FROM events WHERE request_id=? AND event!='reserved'",
                (request_id,),
            ).fetchone()
            if not terminal:
                self.ledger.append(request_id, "billing_unknown")
            raise
        except Exception as exc:
            terminal = self.ledger.db.execute(
                "SELECT 1 FROM events WHERE request_id=? AND event!='reserved'",
                (request_id,),
            ).fetchone()
            if not terminal:
                self.ledger.append(request_id, "failed", metadata=json.dumps({
                    "reason": "provider_request_failed",
                    "error_type": type(exc).__name__,
                    "partner_exception": True,
                }, sort_keys=True))
            raise
        if reported_cost_exceeds_reservation(result.cost, reserved):
            self.ledger.append(request_id, "billing_unknown", actual=result.cost,
                               metadata=json.dumps({
                                   "provider_request_id": result.provider_request_id,
                                   "output_url": audit_safe_url(result.output_url),
                                   "request_sha256": planned.prompt_sha256,
                                   "reason": "reported_cost_exceeded_reservation",
                               }, sort_keys=True))
            raise UnknownBillingStatus("reported cost exceeded approved reservation")
        destination = Path(output_dir) / f"{request_id}.mp4"
        base_metadata = {
            "provider_request_id": result.provider_request_id,
            "output_url": audit_safe_url(result.output_url),
            "output_path": str(destination),
            "request_sha256": planned.prompt_sha256,
            "image_sha256": safe_payload["image_sha256"],
            "partner_exception": True,
            "licence_status": "not_reported_by_provider",
        }
        if "audio_sha256" in safe_payload:
            base_metadata["audio_sha256"] = safe_payload["audio_sha256"]
        try:
            output_sha256 = client.download(result.output_url, str(destination))
        except Exception:
            self.ledger.append(request_id, "failed", actual=result.cost,
                               metadata=json.dumps({**base_metadata, "reason": "download_failed"},
                                                   sort_keys=True))
            raise
        self.ledger.append(
            request_id, "completed", actual=result.cost,
            metadata=json.dumps({**base_metadata, "output_sha256": output_sha256}, sort_keys=True),
        )
        return PlannedRequest(
            request_id,
            model.id,
            reserved,
            planned.prompt_sha256,
            False,
            output_path=str(destination),
            output_sha256=output_sha256,
            provider_request_id=result.provider_request_id,
        )

    def run_speech(self, text: str, *, seed: int = 0, output_format: str = "wav",
                   live: bool = False, confirmed: bool = False,
                   voice_realization: dict[str, Any] | None = None,
                   client: DeepInfraClient | None = None,
                   output_dir: str | Path = "outputs") -> PlannedRequest:
        if not text.strip():
            raise PolicyError("speech text is required")
        if len(text) > 500:
            raise PolicyError("speech text exceeds the 500 character test limit")
        if output_format != "wav":
            raise PolicyError("the proof accepts WAV speech only")
        client = self._client_for_live(live=live, confirmed=confirmed, client=client)
        model = self.config.model("speech")
        binding = self._voice_binding(
            voice_realization, model_id=model.id, live=live, seed=seed,
        )
        if binding is not None:
            configured_format = binding["immutable_settings"].get("response_format")
            if configured_format is not None and configured_format != output_format:
                raise PolicyError(
                    "request-time output format conflicts with canonical realization"
                )
        if self.ledger.reservation_count(model.id) >= 8:
            raise PolicyError("speech request cap reached")
        payload = {"text": text, "response_format": output_format, "seed": seed}
        reserved = model.reserve(characters=len(text))
        request_id = str(uuid.uuid4())
        self.ledger.reserve(request_id, model.id, reserved, self.cap)
        request_audit = {"provider_payload": payload}
        if binding is not None:
            request_audit["voice_realization_sha256"] = voice_realization_sha256(binding)
        planned = PlannedRequest(
            request_id, model.id, reserved, prompt_hash(request_audit), not live,
        )
        if not live:
            return planned
        assert client is not None
        try:
            result = client.infer_audio(model.id, payload)
        except UnknownBillingStatus:
            self.ledger.append(request_id, "billing_unknown")
            raise
        except Exception:
            self.ledger.append(request_id, "failed")
            raise
        if reported_cost_exceeds_reservation(result.cost, reserved):
            self.ledger.append(request_id, "billing_unknown", actual=result.cost,
                               metadata=json.dumps({
                                   "provider_request_id": result.provider_request_id,
                                   "output_url": audit_safe_url(result.output_url),
                                   "request_sha256": planned.prompt_sha256,
                                   "reason": "reported_cost_exceeded_reservation",
                               }, sort_keys=True))
            raise UnknownBillingStatus("reported cost exceeded approved reservation")
        destination = Path(output_dir) / f"{request_id}.wav"
        base_metadata = {"provider_request_id": result.provider_request_id,
                         "output_url": audit_safe_url(result.output_url),
                         "output_path": str(destination),
                         "text_sha256": prompt_hash({"text": text}),
                         "request_sha256": planned.prompt_sha256,
                         "output_format": output_format,
                         "words": result.raw.get("words", [])}
        if binding is not None:
            base_metadata.update({
                "voice_realization_id": binding["voice_realization_id"],
                "voice_realization_sha256": voice_realization_sha256(binding),
                "audition_sha256": binding["approval"]["audition_sha256"],
            })
        try:
            output_sha256 = client.download(result.output_url, str(destination))
        except Exception:
            self.ledger.append(request_id, "failed", actual=result.cost,
                               metadata=json.dumps({**base_metadata, "reason": "download_failed"},
                                                   sort_keys=True))
            raise
        metadata = json.dumps({**base_metadata, "output_sha256": output_sha256}, sort_keys=True)
        self.ledger.append(request_id, "completed", actual=result.cost, metadata=metadata)
        return planned

    def run_avatar(self, image_input: str, voice_script: str, voice: str, *,
                   seed: int = 0, max_seconds: int = 8,
                   gaze_direction: str | None = None,
                   speaker_position: str = "only_person",
                   response_anticipation: bool = False,
                   performance_direction: str = "Restrained natural dramatic delivery, conversational pace.",
                   live: bool = False, confirmed: bool = False,
                   allow_partner: bool = False,
                   voice_realization: dict[str, Any] | None = None,
                   client: DeepInfraClient | None = None,
                   output_dir: str | Path = "outputs") -> PlannedRequest:
        if not allow_partner:
            raise PolicyError("partner avatar model requires --allow-partner-avatar")
        image_parts = urlsplit(image_input)
        is_image_data = image_parts.scheme == "data" and image_input.startswith("data:image/")
        is_public_https = (image_parts.scheme == "https" and bool(image_parts.netloc)
                           and image_parts.username is None and image_parts.password is None)
        if not (is_image_data or is_public_https):
            raise PolicyError("avatar input must be an image Data URL or public HTTPS URL")
        if not voice_script.strip() or len(voice_script) > 100:
            raise PolicyError("avatar script must contain 1–100 characters")
        if gaze_direction not in {"screen_left", "screen_right"}:
            raise PolicyError("avatar gaze must be screen_left or screen_right; camera gaze is forbidden")
        if speaker_position not in {"only_person", "frame_left", "frame_right"}:
            raise PolicyError("avatar speaker position must be only_person, frame_left, or frame_right")
        if not performance_direction.strip() or len(performance_direction) > 160:
            raise PolicyError("avatar performance direction must contain 1–160 characters")
        if not 2 <= max_seconds <= 8:
            raise PolicyError("avatar reservation must cover 2–8 seconds")
        client = self._client_for_live(live=live, confirmed=confirmed, client=client)
        model = self.config.model("lip_sync_avatar")
        binding = self._voice_binding(
            voice_realization, model_id=model.id, live=live,
            provider_voice=voice, seed=seed,
        )
        if self.ledger.reservation_count(model.id) >= self.partner_avatar_attempt_cap:
            raise PolicyError("partner avatar request cap reached")
        if speaker_position == "only_person":
            subject_direction = str(model.data.get("single_subject_prompt", "")).strip()
            if not subject_direction:
                raise PolicyError("avatar model configuration lacks single_subject_prompt")
        else:
            speaker_side = speaker_position.replace("frame_", "frame ")
            listener_side = "frame right" if speaker_position == "frame_left" else "frame left"
            paired_template = str(
                model.data.get("paired_subject_prompt_template", "")
            ).strip()
            if not paired_template:
                raise PolicyError("avatar model configuration lacks paired_subject_prompt_template")
            subject_direction = paired_template.format(
                speaker_side=speaker_side, listener_side=listener_side
            )
        anticipation_direction = ""
        if response_anticipation:
            anticipation_template = str(
                model.data.get("response_anticipation_prompt", "")
            ).strip()
            if not anticipation_template:
                raise PolicyError(
                    "avatar model configuration lacks response_anticipation_prompt"
                )
            anticipation_direction = anticipation_template.format(
                gaze_direction=gaze_direction.replace("_", " ")
            ) + " "
        gaze_template = str(model.data.get("gaze_lock_prompt_template", "")).strip()
        if not gaze_template:
            raise PolicyError("avatar model configuration lacks gaze_lock_prompt_template")
        gaze_direction_text = gaze_direction.replace("_", " ")
        gaze_direction_prompt = gaze_template.format(gaze_direction=gaze_direction_text)
        payload = {
            "image": image_input,
            "voice_script": voice_script,
            "voice": voice,
            "voice_language": "English (US)",
            "voice_prompt": performance_direction,
            "video_prompt": (
                f"{subject_direction} "
                f"{anticipation_direction}"
                f"{gaze_direction_prompt}"
            ),
            "resolution": "720p",
            "seed": seed,
            "disable_safety_filter": False,
            "disable_prompt_upsampling": False,
        }
        reserved = model.reserve(seconds=max_seconds)
        request_id = str(uuid.uuid4())
        partner_policy_cap = Decimal(str(
            self.config.raw["provider_policy"]["explicit_partner_test_exception"]
            ["additional_run_cap_usd"]
        ))
        reservation_cap = self.cap if self.explicit_run_cap else min(self.cap, partner_policy_cap)
        self.ledger.reserve(request_id, model.id, reserved, reservation_cap)
        safe_payload = {key: value for key, value in payload.items() if key != "image"}
        # Persist only a digest of the input, never an inline image or a
        # temporary third-party transport URL.
        safe_payload["image_sha256"] = prompt_hash({"image": image_input})
        if binding is not None:
            safe_payload["voice_realization_sha256"] = voice_realization_sha256(binding)
        planned = PlannedRequest(request_id, model.id, reserved, prompt_hash(safe_payload), not live)
        if not live:
            return planned
        assert client is not None
        try:
            result = client.infer(model.id, payload)
        except UnknownBillingStatus:
            self.ledger.append(request_id, "billing_unknown")
            raise
        except Exception as exc:
            self.ledger.append(request_id, "failed", metadata=json.dumps({
                "reason": "provider_request_failed",
                "error_type": type(exc).__name__,
                "partner_exception": True,
            }, sort_keys=True))
            raise
        if reported_cost_exceeds_reservation(result.cost, reserved):
            self.ledger.append(request_id, "billing_unknown", actual=result.cost,
                               metadata=json.dumps({
                                   "provider_request_id": result.provider_request_id,
                                   "output_url": audit_safe_url(result.output_url),
                                   "request_sha256": planned.prompt_sha256,
                                   "reason": "reported_cost_exceeded_reservation",
                               }, sort_keys=True))
            raise UnknownBillingStatus("reported cost exceeded approved reservation")
        destination = Path(output_dir) / f"{request_id}.mp4"
        base_metadata = {
            "provider_request_id": result.provider_request_id,
            "output_url": audit_safe_url(result.output_url),
            "output_path": str(destination),
            "request_sha256": planned.prompt_sha256,
            "voice": voice,
            "gaze_direction": gaze_direction,
            "speaker_position": speaker_position,
            "response_anticipation": response_anticipation,
            "performance_sha256": prompt_hash({"performance_direction": performance_direction}),
            "script_sha256": prompt_hash({"voice_script": voice_script}),
            "partner_exception": True,
            "licence_status": "not_reported_by_provider",
        }
        if binding is not None:
            base_metadata.update({
                "voice_realization_id": binding["voice_realization_id"],
                "voice_realization_sha256": voice_realization_sha256(binding),
                "audition_sha256": binding["approval"]["audition_sha256"],
            })
        try:
            output_sha256 = client.download(result.output_url, str(destination))
        except Exception:
            self.ledger.append(request_id, "failed", actual=result.cost,
                               metadata=json.dumps({**base_metadata, "reason": "download_failed"},
                                                   sort_keys=True))
            raise
        metadata = json.dumps({**base_metadata, "output_sha256": output_sha256}, sort_keys=True)
        self.ledger.append(request_id, "completed", actual=result.cost, metadata=metadata)
        return planned
