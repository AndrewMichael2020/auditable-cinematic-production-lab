from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .errors import PolicyError


VOICE_REALIZATION_ID = re.compile(r"^vr-[0-9a-z][0-9a-z-]*-v[0-9]+$")
PERSONA_VERSION = re.compile(r"^pv[0-9]+$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
APPROVAL_STATUSES = {
    "not_auditioned",
    "pending_human_audition",
    "approved",
    "rejected",
}
SENSITIVE_SETTING_PARTS = ("token", "secret", "password", "api_key", "credential")


def validate_voice_realization(
    realization: Any, *, persona_version: str | None = None,
    require_approved: bool = False,
) -> dict[str, Any]:
    """Validate one versioned voice binding without accepting request-time overrides."""
    if not isinstance(realization, dict):
        raise PolicyError("voice realization must be an object")
    for field in (
        "voice_realization_id", "effective_persona_version", "provider_model_id",
        "provider_voice", "approval",
    ):
        if field not in realization:
            raise PolicyError(f"voice realization requires {field}")
    realization_id = str(realization["voice_realization_id"]).strip()
    if not VOICE_REALIZATION_ID.fullmatch(realization_id):
        raise PolicyError(f"invalid voice_realization_id: {realization_id!r}")
    effective_version = str(realization["effective_persona_version"]).strip()
    if not PERSONA_VERSION.fullmatch(effective_version):
        raise PolicyError("voice realization has invalid effective_persona_version")
    if persona_version is not None and effective_version != persona_version:
        raise PolicyError("voice realization persona version does not match canonical persona")
    for field in ("provider_model_id", "provider_voice"):
        if not str(realization[field]).strip():
            raise PolicyError(f"voice realization requires non-empty {field}")
    settings = realization.get("immutable_settings")
    if not isinstance(settings, dict) or not settings:
        raise PolicyError("voice realization requires immutable_settings")
    for key, value in settings.items():
        normalized_key = str(key).lower()
        if any(part in normalized_key for part in SENSITIVE_SETTING_PARTS):
            raise PolicyError("voice realization settings must not contain credentials")
        if not isinstance(value, (str, int, float, bool)) or isinstance(value, float) and value != value:
            raise PolicyError("voice realization settings must contain finite scalar values")
    approval = realization["approval"]
    if not isinstance(approval, dict):
        raise PolicyError("voice realization approval must be an object")
    status = str(approval.get("status", "")).strip()
    if status not in APPROVAL_STATUSES:
        raise PolicyError(f"invalid voice realization approval status: {status!r}")
    audition_path = str(approval.get("audition_path") or "").strip()
    audition_sha256 = str(approval.get("audition_sha256") or "").strip()
    if bool(audition_path) != bool(audition_sha256):
        raise PolicyError("voice audition path and SHA-256 must be supplied together")
    if audition_sha256 and not SHA256.fullmatch(audition_sha256):
        raise PolicyError("voice audition SHA-256 must be 64 lowercase hexadecimal characters")
    if status == "approved":
        for field in ("audition_path", "audition_sha256", "reviewed_by", "reviewed_at"):
            if not str(approval.get(field) or "").strip():
                raise PolicyError(f"approved voice realization requires {field}")
    if require_approved and status != "approved":
        raise PolicyError(f"voice realization {realization_id} is not human-approved")
    return realization


def voice_realization_sha256(realization: dict[str, Any]) -> str:
    """Return a stable digest for the complete binding recorded with a request."""
    validate_voice_realization(realization)
    canonical = json.dumps(realization, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()
