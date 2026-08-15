from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import PolicyError


DEFAULT_TARGET_MAX_OFFSET_MS = 80.0
DEFAULT_MAX_MEASUREMENT_CADENCE_MS = 40.0
DEFAULT_MIN_CONFIDENCE = 0.80
EVIDENCE_KINDS = {"artifact_measurement", "calibration_fixture"}
HUMAN_DECISIONS = {"pass", "fail", "pending"}


def _number(value: Any, field: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool):
        raise PolicyError(f"{field} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PolicyError(f"{field} must be numeric") from exc
    if number < minimum or number != number or number in {float("inf"), float("-inf")}:
        raise PolicyError(f"{field} must be finite and at least {minimum}")
    return number


def audit_av_sync(evidence: dict[str, Any]) -> dict[str, Any]:
    """Evaluate timestamped audiovisual-onset evidence without claiming visual inference.

    The caller supplies independently measured audio and visual onset timestamps. This function
    validates the evidence cadence, confidence, and offset bound; it does not detect mouth motion
    from media. Final acceptance additionally requires an artifact measurement and normal-speed
    human review with sound.
    """
    if not isinstance(evidence, dict):
        raise PolicyError("AV-sync evidence must be a JSON object")
    kind = str(evidence.get("evidence_kind", ""))
    if kind not in EVIDENCE_KINDS:
        raise PolicyError(
            "evidence_kind must be artifact_measurement or calibration_fixture"
        )
    artifact_id = str(evidence.get("artifact_id", "")).strip()
    if not artifact_id:
        raise PolicyError("artifact_id is required")

    target = _number(
        evidence.get("target_max_absolute_offset_ms", DEFAULT_TARGET_MAX_OFFSET_MS),
        "target_max_absolute_offset_ms",
        minimum=1.0,
    )
    cadence = _number(
        evidence.get("measurement_cadence_ms"), "measurement_cadence_ms", minimum=0.001
    )
    maximum_cadence = min(DEFAULT_MAX_MEASUREMENT_CADENCE_MS, target / 2.0)
    cadence_capable = cadence <= maximum_cadence

    events = evidence.get("events")
    if not isinstance(events, list) or len(events) < 2:
        raise PolicyError("AV-sync evidence requires at least two timestamped events")

    normalized_events: list[dict[str, Any]] = []
    event_ids: set[str] = set()
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise PolicyError(f"events[{index}] must be an object")
        event_id = str(event.get("event_id", "")).strip()
        if not event_id or event_id in event_ids:
            raise PolicyError("event_id values must be unique and non-empty")
        event_ids.add(event_id)
        audio_onset = _number(
            event.get("audio_onset_ms"), f"events[{index}].audio_onset_ms"
        )
        visual_onset = _number(
            event.get("visual_onset_ms"), f"events[{index}].visual_onset_ms"
        )
        confidence = _number(
            event.get("confidence"), f"events[{index}].confidence"
        )
        if confidence > 1.0:
            raise PolicyError(f"events[{index}].confidence must be between 0 and 1")
        signed_offset = visual_onset - audio_onset
        normalized_events.append({
            "event_id": event_id,
            "audio_onset_ms": round(audio_onset, 3),
            "visual_onset_ms": round(visual_onset, 3),
            "signed_offset_ms": round(signed_offset, 3),
            "absolute_offset_ms": round(abs(signed_offset), 3),
            "confidence": round(confidence, 3),
            "within_target": abs(signed_offset) <= target,
        })

    maximum_offset = max(item["absolute_offset_ms"] for item in normalized_events)
    minimum_confidence = min(item["confidence"] for item in normalized_events)
    offsets_pass = all(item["within_target"] for item in normalized_events)
    confidence_pass = minimum_confidence >= DEFAULT_MIN_CONFIDENCE
    objective_gate = "pass" if cadence_capable and offsets_pass and confidence_pass else "fail"

    human = evidence.get("human_review", {})
    if not isinstance(human, dict):
        raise PolicyError("human_review must be an object")
    decision = str(human.get("decision", "pending"))
    if decision not in HUMAN_DECISIONS:
        raise PolicyError("human_review.decision must be pass, fail, or pending")
    normal_speed = human.get("normal_speed") is True
    sound_enabled = human.get("sound_enabled") is True
    reviewer_value = human.get("reviewer")
    reviewer = (
        reviewer_value.strip()
        if isinstance(reviewer_value, str) and reviewer_value.strip()
        else None
    )

    if kind == "calibration_fixture":
        acceptance_gate = "not_applicable"
    elif objective_gate == "fail" or decision == "fail":
        acceptance_gate = "fail"
    elif decision == "pass" and normal_speed and sound_enabled and reviewer:
        acceptance_gate = "pass"
    else:
        acceptance_gate = "review"

    return {
        "schema_version": "1.0",
        "audit_type": "audiovisual_offset",
        "artifact_id": artifact_id,
        "evidence_kind": kind,
        "target_max_absolute_offset_ms": round(target, 3),
        "measurement_cadence_ms": round(cadence, 3),
        "maximum_allowed_cadence_ms": round(maximum_cadence, 3),
        "cadence_capable": cadence_capable,
        "minimum_required_confidence": DEFAULT_MIN_CONFIDENCE,
        "minimum_observed_confidence": minimum_confidence,
        "maximum_absolute_offset_ms": maximum_offset,
        "objective_gate": objective_gate,
        "human_review": {
            "decision": decision,
            "normal_speed": normal_speed,
            "sound_enabled": sound_enabled,
            "reviewer": reviewer,
        },
        "acceptance_gate": acceptance_gate,
        "events": normalized_events,
        "limitations": (
            "Timestamp evidence is supplied by the measurement process; this evaluator does not "
            "infer lip motion. A calibration fixture validates evaluator resolution only and cannot "
            "establish synchronization of a production artifact."
        ),
    }


def audit_av_sync_file(path: str | Path) -> dict[str, Any]:
    try:
        evidence = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(f"cannot read AV-sync evidence: {exc}") from exc
    return audit_av_sync(evidence)
