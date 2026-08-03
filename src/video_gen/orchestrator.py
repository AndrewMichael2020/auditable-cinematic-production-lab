from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from .config import ProjectConfig
from .errors import PolicyError, UnknownBillingStatus
from .ledger import Ledger
from .provider import DeepInfraClient, prompt_hash

COST_COMPARISON_EPSILON = Decimal("0.000000000001")
MAX_PARTNER_AVATAR_ATTEMPTS = 5


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


class Orchestrator:
    def __init__(self, config: ProjectConfig, ledger: Ledger, profile: str):
        self.config = config
        self.ledger = ledger
        self.profile = profile
        self.cap = config.profile_cap(profile)

    def run_video(self, role: str, prompt: str, *, seconds: int = 5, seed: int = 0,
                  live: bool = False, confirmed: bool = False,
                  client: DeepInfraClient | None = None,
                  output_dir: str | Path = "outputs") -> PlannedRequest:
        if role not in {"draft_video", "final_video"}:
            raise PolicyError("run_video accepts approved video roles only")
        if role == "final_video" and live and not confirmed:
            raise PolicyError("final generation requires explicit human promotion")
        if live and not confirmed:
            raise PolicyError("live request requires --confirm-live")
        if live and client is None:
            # Validate credentials before creating a budget reservation. A local
            # configuration error must not leave an orphan paid-attempt record.
            client = DeepInfraClient(os.environ.get("DEEPINFRA_TOKEN", ""))
        model = self.config.model(role)
        profile_data = self.config.raw["budget"]["profiles"][self.profile]
        count_key = "max_fastwan_5s_drafts" if role == "draft_video" else "max_wan22_5s_finals"
        if self.ledger.reservation_count(model.id) >= int(profile_data[count_key]):
            raise PolicyError(f"candidate cap reached for {role}")
        configured_seconds = int(model.data["seconds"])
        if seconds != configured_seconds:
            raise PolicyError(f"{model.id} is approved for exactly {configured_seconds} seconds")
        payload = {"prompt": prompt, "duration": seconds, "seed": seed}
        reserved = model.reserve(seconds=seconds)
        request_id = str(uuid.uuid4())
        self.ledger.reserve(request_id, model.id, reserved, self.cap)
        planned = PlannedRequest(request_id, model.id, reserved, prompt_hash(payload), not live)
        if not live:
            return planned
        assert client is not None
        try:
            result = client.infer(model.id, payload)
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
        return planned

    def run_speech(self, text: str, *, seed: int = 0, output_format: str = "wav",
                   live: bool = False, confirmed: bool = False,
                   client: DeepInfraClient | None = None,
                   output_dir: str | Path = "outputs") -> PlannedRequest:
        if not text.strip():
            raise PolicyError("speech text is required")
        if len(text) > 500:
            raise PolicyError("speech text exceeds the 500 character test limit")
        if output_format != "wav":
            raise PolicyError("the proof accepts WAV speech only")
        if live and not confirmed:
            raise PolicyError("live request requires --confirm-live")
        if live and client is None:
            client = DeepInfraClient(os.environ.get("DEEPINFRA_TOKEN", ""))
        model = self.config.model("speech")
        if self.ledger.reservation_count(model.id) >= 8:
            raise PolicyError("speech request cap reached")
        payload = {"text": text, "response_format": output_format, "seed": seed}
        reserved = model.reserve(characters=len(text))
        request_id = str(uuid.uuid4())
        self.ledger.reserve(request_id, model.id, reserved, self.cap)
        planned = PlannedRequest(request_id, model.id, reserved, prompt_hash(payload), not live)
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
                   performance_direction: str = "Restrained natural dramatic delivery, conversational pace.",
                   live: bool = False, confirmed: bool = False,
                   allow_partner: bool = False,
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
        if not performance_direction.strip() or len(performance_direction) > 160:
            raise PolicyError("avatar performance direction must contain 1–160 characters")
        if not 2 <= max_seconds <= 8:
            raise PolicyError("avatar reservation must cover 2–8 seconds")
        if live and not confirmed:
            raise PolicyError("live request requires --confirm-live")
        if live and client is None:
            client = DeepInfraClient(os.environ.get("DEEPINFRA_TOKEN", ""))
        model = self.config.model("lip_sync_avatar")
        if self.ledger.reservation_count(model.id) >= MAX_PARTNER_AVATAR_ATTEMPTS:
            raise PolicyError("partner avatar request cap reached")
        payload = {
            "image": image_input,
            "voice_script": voice_script,
            "voice": voice,
            "voice_language": "English (US)",
            "voice_prompt": performance_direction,
            "video_prompt": (
                f"Locked camera, strict static side-profile conversation shot facing {gaze_direction.replace('_', ' ')}. "
                f"For every frame the nose, face, and pupils remain aimed {gaze_direction.replace('_', ' ')} "
                "at the off-camera scene partner. Preserve the reference head angle. No head turn. "
                "No frontal pose. No eye contact with the camera, lens, viewer, or center lens axis. "
                "Only the lips, jaw, eyebrows, and breathing move; the camera is an unnoticed observer."
            ),
            "resolution": "720p",
            "seed": seed,
            "disable_safety_filter": False,
            "disable_prompt_upsampling": False,
        }
        reserved = model.reserve(seconds=max_seconds)
        request_id = str(uuid.uuid4())
        self.ledger.reserve(request_id, model.id, reserved, min(self.cap, Decimal("3")))
        safe_payload = {key: value for key, value in payload.items() if key != "image"}
        # Persist only a digest of the input, never an inline image or a
        # temporary third-party transport URL.
        safe_payload["image_sha256"] = prompt_hash({"image": image_input})
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
            "performance_sha256": prompt_hash({"performance_direction": performance_direction}),
            "script_sha256": prompt_hash({"voice_script": voice_script}),
            "partner_exception": True,
            "licence_status": "not_reported_by_provider",
        }
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
