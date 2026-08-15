from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Any

from .errors import PolicyError
from .media import sha256_file
from .voice_casting import validate_matching_profile


SCHEMA_VERSION = "1.0"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
VOICE_AUDITION_CRITERIA = (
    "perceived_age",
    "gender_presentation",
    "timbre",
    "accent",
    "diction",
    "pace",
    "intelligibility",
    "dramatic_fit",
)
DOT_SEPARATED_ACRONYM_PATTERN = re.compile(r"\b(?:[A-Z]\.){2,}(?:[A-Z]\.)?")


def _load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _resolve(owner: Path, value: str) -> Path:
    candidate = Path(value)
    return candidate if candidate.is_absolute() else owner.parent / candidate


def _require_string(packet: dict[str, Any], field: str, context: str) -> str:
    value = str(packet.get(field, "")).strip()
    if not value:
        raise PolicyError(f"{context} requires {field}")
    return value


def _reject_dotted_acronyms(value: str, context: str) -> None:
    """Keep spoken acronyms compact so synthesis does not insert artificial pauses."""
    if DOT_SEPARATED_ACRONYM_PATTERN.search(value):
        raise PolicyError(f"{context} must not contain dot-separated acronyms")


def _validate_voice(persona: dict[str, Any], series_path: Path) -> None:
    context = f"persona {persona.get('character_id', '<unknown>')} voice"
    voice = persona.get("voice")
    if not isinstance(voice, dict) or voice.get("contract_version") != SCHEMA_VERSION:
        raise PolicyError(f"{context} requires voice contract_version {SCHEMA_VERSION}")
    for field in (
        "voice_persona_id",
        "perceived_age_range",
        "gender_presentation",
        "timbre",
        "register",
        "vocal_manner",
        "language_history",
        "accent_diction",
        "pace",
        "energy",
        "recast_policy",
    ):
        _require_string(voice, field, context)
    validate_matching_profile(voice, context=context)

    realizations = voice.get("voice_realizations")
    if not isinstance(realizations, list) or not realizations:
        raise PolicyError(f"{context} requires voice_realizations")
    realization_ids: set[str] = set()
    for index, realization in enumerate(realizations):
        realization_context = f"{context} realization {index}"
        if not isinstance(realization, dict):
            raise PolicyError(f"{realization_context} must be an object")
        realization_id = _require_string(
            realization, "voice_realization_id", realization_context
        )
        if not re.fullmatch(r"vr-[0-9a-z][0-9a-z-]*", realization_id):
            raise PolicyError(f"{realization_context} has an invalid voice_realization_id")
        if realization_id in realization_ids:
            raise PolicyError(f"{context} realization ids must be unique")
        realization_ids.add(realization_id)
        if realization.get("persona_version") != persona.get("persona_version"):
            raise PolicyError(f"{realization_context} persona_version is not canonical")
        for field in ("provider", "model_id", "model_version"):
            _require_string(realization, field, realization_context)
        settings = realization.get("synthesis_settings")
        if not isinstance(settings, dict) or not settings:
            raise PolicyError(f"{realization_context} requires synthesis_settings")
        for field in ("voice", "instruct", "language", "response_format"):
            _require_string(settings, field, f"{realization_context} settings")
        if settings["response_format"] != "wav":
            raise PolicyError(f"{realization_context} auditions must use WAV")
        status = realization.get("status")
        if status not in {"planned", "candidate", "approved", "rejected", "retired"}:
            raise PolicyError(f"{realization_context} has an invalid status")
        audition = realization.get("audition")
        if not isinstance(audition, dict):
            raise PolicyError(f"{realization_context} requires an audition")
        audition_script = _require_string(
            audition, "script", f"{realization_context} audition"
        )
        _reject_dotted_acronyms(audition_script, f"{realization_context} audition script")
        audio_path_value = _require_string(
            audition, "audio_path", f"{realization_context} audition"
        )
        audio_sha256 = audition.get("audio_sha256")
        if audio_sha256 is not None and not SHA256_PATTERN.fullmatch(str(audio_sha256)):
            raise PolicyError(f"{realization_context} audition has an invalid SHA-256")
        if status in {"candidate", "approved", "rejected", "retired"}:
            audio_path = _resolve(series_path, audio_path_value)
            if not audio_sha256 or not audio_path.is_file():
                raise PolicyError(f"{realization_context} audition audio is missing")
            if sha256_file(audio_path) != audio_sha256:
                raise PolicyError(f"{realization_context} audition hash does not match")
            _require_string(audition, "provider_request_id", f"{realization_context} audition")
        review = audition.get("review")
        if not isinstance(review, dict):
            raise PolicyError(f"{realization_context} audition requires structured review")
        decision = review.get("decision")
        if decision not in {"pending", "approved", "rejected"}:
            raise PolicyError(f"{realization_context} audition decision is invalid")
        criteria = review.get("criteria")
        if not isinstance(criteria, dict) or set(criteria) != set(VOICE_AUDITION_CRITERIA):
            raise PolicyError(f"{realization_context} audition criteria are incomplete")
        if any(value not in {"pending", "pass", "fail"} for value in criteria.values()):
            raise PolicyError(f"{realization_context} audition criterion is invalid")
        if status == "approved":
            if decision != "approved" or any(
                criteria[field] != "pass" for field in VOICE_AUDITION_CRITERIA
            ):
                raise PolicyError(
                    f"{realization_context} cannot be approved without a passing human audition"
                )
            _require_string(realization, "effective_from", realization_context)
            _require_string(review, "reviewer", f"{realization_context} audition review")
            _require_string(review, "reviewed_at", f"{realization_context} audition review")

    active_id = voice.get("active_voice_realization_id")
    if active_id is not None:
        if active_id not in realization_ids:
            raise PolicyError(f"{context} active realization is unknown")
        active = next(
            item for item in realizations if item["voice_realization_id"] == active_id
        )
        if active["status"] != "approved":
            raise PolicyError(f"{context} active realization must be approved")


def load_voice_plan(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    packet = _load(source)
    if packet.get("schema_version") != SCHEMA_VERSION:
        raise PolicyError(f"voice plan requires schema_version {SCHEMA_VERSION}")
    for field in ("sequence_id", "title", "source_run"):
        _require_string(packet, field, "voice plan")
    source_run = _resolve(source, str(packet["source_run"]))
    if not source_run.is_dir():
        raise PolicyError("voice plan source_run does not exist")
    series_path = _resolve(
        source, _require_string(packet, "series_manifest", "voice plan")
    )
    if not series_path.is_file():
        raise PolicyError("voice plan series_manifest does not exist")
    series = _load(series_path)
    personas = {
        item.get("character_id"): item
        for item in series.get("canonical_personas", [])
        if isinstance(item, dict) and item.get("character_id")
    }
    bindings = packet.get("persona_bindings")
    if not isinstance(bindings, list) or not bindings:
        raise PolicyError("voice plan requires persona_bindings")
    bound_personas: dict[str, dict[str, Any]] = {}
    for binding in bindings:
        if not isinstance(binding, dict):
            raise PolicyError("voice plan persona binding must be an object")
        character_id = _require_string(binding, "character_id", "persona binding")
        if character_id in bound_personas or character_id not in personas:
            raise PolicyError("voice plan persona binding must reference one unique persona")
        persona = personas[character_id]
        if binding.get("persona_version") != persona.get("persona_version"):
            raise PolicyError("voice plan persona_version is not canonical")
        _validate_voice(persona, series_path)
        bound_personas[character_id] = persona

    anchor = packet.get("visual_anchor")
    if not isinstance(anchor, dict):
        raise PolicyError("voice plan requires visual_anchor")
    anchor_path = _resolve(source, _require_string(anchor, "path", "visual anchor"))
    anchor_sha = _require_string(anchor, "sha256", "visual anchor")
    if not anchor_path.is_file() or sha256_file(anchor_path) != anchor_sha:
        raise PolicyError("voice plan visual anchor is missing or hash-mismatched")

    masters = packet.get("performance_masters")
    if not isinstance(masters, list) or not masters:
        raise PolicyError("voice plan requires performance_masters")
    master_by_id: dict[str, dict[str, Any]] = {}
    master_dialogue_ids: list[str] = []
    for master in masters:
        if not isinstance(master, dict):
            raise PolicyError("performance master must be an object")
        master_id = _require_string(master, "performance_master_id", "performance master")
        if not re.fullmatch(r"pm-[0-9a-z][0-9a-z-]*", master_id) or master_id in master_by_id:
            raise PolicyError("performance master id is invalid or duplicated")
        master_by_id[master_id] = master
        character_id = _require_string(master, "character_id", "performance master")
        if character_id not in bound_personas:
            raise PolicyError("performance master character is not bound")
        if master.get("persona_version") != bound_personas[character_id]["persona_version"]:
            raise PolicyError("performance master persona_version is not canonical")
        realization_id = _require_string(
            master, "voice_realization_id", "performance master"
        )
        realization_ids = {
            item["voice_realization_id"]
            for item in bound_personas[character_id]["voice"]["voice_realizations"]
        }
        if realization_id not in realization_ids:
            raise PolicyError("performance master voice realization is unknown")
        master_status = master.get("status")
        if master_status not in {"planned", "candidate", "approved", "rejected"}:
            raise PolicyError("performance master status is invalid")
        master_audio_path = _require_string(
            master, "audio_path", "performance master"
        )
        master_sha = master.get("sha256")
        master_audition_sha = master.get("audition_sha256")
        for label, value in (
            ("sha256", master_sha), ("audition_sha256", master_audition_sha)
        ):
            if value is not None and not SHA256_PATTERN.fullmatch(str(value)):
                raise PolicyError(f"performance master {label} is invalid")
        if master_status in {"candidate", "approved", "rejected"}:
            resolved_master = _resolve(source, master_audio_path)
            if not master_sha or not resolved_master.is_file():
                raise PolicyError("performance master audio is missing")
            if sha256_file(resolved_master) != master_sha:
                raise PolicyError("performance master hash does not match")
        dialogue_ids = master.get("dialogue_ids")
        if not isinstance(dialogue_ids, list) or not dialogue_ids:
            raise PolicyError("performance master requires dialogue_ids")
        master_dialogue_ids.extend(str(item) for item in dialogue_ids)

    beats = packet.get("beats")
    if not isinstance(beats, list) or not beats:
        raise PolicyError("voice plan requires beats")
    dialogue_ids: set[str] = set()
    speaking_characters: set[str] = set()
    lines_by_character: dict[str, list[str]] = {}
    for beat in beats:
        if not isinstance(beat, dict):
            raise PolicyError("voice plan beat must be an object")
        _require_string(beat, "beat_id", "voice plan beat")
        duration = float(beat.get("seconds", 0))
        omitted = str(beat.get("status", "")).startswith("omitted_")
        if duration < 0 or (duration == 0 and not omitted):
            raise PolicyError(
                "voice plan beat duration must be positive unless the beat is omitted"
            )
        speaker = beat.get("speaker")
        line = beat.get("line")
        if speaker is None and line is None:
            if beat.get("voice_binding") is not None:
                raise PolicyError("silent beat cannot carry a voice_binding")
            continue
        if speaker not in bound_personas or not str(line or "").strip():
            raise PolicyError("spoken beat requires a bound speaker and line")
        _reject_dotted_acronyms(str(line), f"beat {beat['beat_id']} line")
        dialogue_id = _require_string(beat, "dialogue_id", "spoken beat")
        if dialogue_id in dialogue_ids:
            raise PolicyError("dialogue ids must be unique")
        dialogue_ids.add(dialogue_id)
        speaking_characters.add(speaker)
        lines_by_character.setdefault(speaker, []).append(str(line))
        voice_binding = beat.get("voice_binding")
        if not isinstance(voice_binding, dict):
            raise PolicyError("spoken beat requires a voice_binding")
        persona = bound_personas[speaker]
        voice = persona["voice"]
        if voice_binding.get("persona_version") != persona["persona_version"]:
            raise PolicyError("beat voice_binding persona_version is not canonical")
        if voice_binding.get("voice_persona_id") != voice["voice_persona_id"]:
            raise PolicyError("beat voice_binding voice_persona_id is not canonical")
        realization_id = _require_string(
            voice_binding, "voice_realization_id", "beat voice_binding"
        )
        realization = next(
            (item for item in voice["voice_realizations"]
             if item["voice_realization_id"] == realization_id),
            None,
        )
        if realization is None:
            raise PolicyError("beat voice_binding realization is unknown")
        audition_hash = realization["audition"].get("audio_sha256")
        if voice_binding.get("audition_sha256") != audition_hash:
            raise PolicyError("beat voice_binding audition hash is not canonical")
        master_id = _require_string(
            voice_binding, "performance_master_id", "beat voice_binding"
        )
        master = master_by_id.get(master_id)
        if (
            master is None
            or master["character_id"] != speaker
            or master["voice_realization_id"] != realization_id
            or dialogue_id not in master["dialogue_ids"]
            or master.get("audition_sha256") != audition_hash
        ):
            raise PolicyError("beat voice_binding conflicts with its performance master")

    if sorted(master_dialogue_ids) != sorted(dialogue_ids):
        raise PolicyError("performance masters must cover every dialogue exactly once")
    if speaking_characters != set(bound_personas):
        raise PolicyError("every bound persona must speak in the voice plan")
    for character_id, lines in lines_by_character.items():
        realization_ids = {
            beat["voice_binding"]["voice_realization_id"]
            for beat in beats if beat.get("speaker") == character_id
        }
        if len(realization_ids) != 1:
            raise PolicyError("one persona cannot use multiple voice realizations in a sequence")
        realization_id = next(iter(realization_ids))
        realization = next(
            item for item in bound_personas[character_id]["voice"]["voice_realizations"]
            if item["voice_realization_id"] == realization_id
        )
        audition_script = " ".join(realization["audition"]["script"].split())
        if any(" ".join(line.split()) not in audition_script for line in lines):
            raise PolicyError("voice audition script must exercise every sequence line")

    packet["_path"] = str(source)
    packet["_series_path"] = str(series_path)
    packet["_personas"] = bound_personas
    packet["_performance_masters"] = master_by_id
    return packet


def voice_audition_spec(plan: dict[str, Any], character_id: str) -> dict[str, Any]:
    persona = plan["_personas"].get(character_id)
    if persona is None:
        raise PolicyError(f"character is not bound in the voice plan: {character_id}")
    realization_ids = {
        beat["voice_binding"]["voice_realization_id"]
        for beat in plan["beats"] if beat.get("speaker") == character_id
    }
    if len(realization_ids) != 1:
        raise PolicyError("voice audition requires one planned realization")
    realization_id = next(iter(realization_ids))
    realization = next(
        item for item in persona["voice"]["voice_realizations"]
        if item["voice_realization_id"] == realization_id
    )
    if realization["status"] != "planned":
        raise PolicyError("voice audition generation accepts planned realizations only")
    return {
        "character_id": character_id,
        "persona_version": persona["persona_version"],
        "voice_persona_id": persona["voice"]["voice_persona_id"],
        "voice_realization_id": realization_id,
        "model_id": realization["model_id"],
        "model_version": realization["model_version"],
        "synthesis_settings": realization["synthesis_settings"],
        "script": realization["audition"]["script"],
        "audio_path": realization["audition"]["audio_path"],
    }


def dialogue_candidate_spec(plan: dict[str, Any]) -> dict[str, Any]:
    """Compile one multi-speaker ElevenLabs candidate from canonical beat bindings."""
    generation = plan.get("dialogue_generation")
    if not isinstance(generation, dict):
        raise PolicyError("voice plan requires dialogue_generation")
    for field in (
        "candidate_id", "model_id", "language_code", "output_format",
        "apply_text_normalization",
    ):
        _require_string(generation, field, "dialogue generation")
    if not isinstance(generation.get("seed"), int):
        raise PolicyError("dialogue generation requires an integer seed")

    inputs: list[dict[str, str]] = []
    turns: list[dict[str, str]] = []
    realization_ids: set[str] = set()
    for beat in plan["beats"]:
        speaker = beat.get("speaker")
        if not speaker:
            continue
        persona = plan["_personas"][speaker]
        binding = beat["voice_binding"]
        realization = next(
            item for item in persona["voice"]["voice_realizations"]
            if item["voice_realization_id"] == binding["voice_realization_id"]
        )
        if realization["provider"] != "elevenlabs":
            raise PolicyError("dialogue generation requires ElevenLabs realizations")
        if realization["model_id"] != generation["model_id"]:
            raise PolicyError("dialogue generation model conflicts with voice realization")
        if realization["status"] != "planned":
            raise PolicyError("new dialogue generation accepts planned realizations only")
        settings = realization["synthesis_settings"]
        voice_id = _require_string(settings, "voice_id", "ElevenLabs realization")
        delivery = _require_string(beat, "delivery", f"beat {beat['beat_id']}")
        line = str(beat["line"]).strip()
        inputs.append({"text": f"[{delivery}] {line}", "voice_id": voice_id})
        turns.append({
            "dialogue_id": beat["dialogue_id"],
            "speaker": speaker,
            "voice_persona_id": persona["voice"]["voice_persona_id"],
            "voice_realization_id": realization["voice_realization_id"],
            "voice_id": voice_id,
            "line": line,
            "delivery": delivery,
        })
        realization_ids.add(realization["voice_realization_id"])
    if len(realization_ids) != len(plan["_personas"]):
        raise PolicyError("dialogue generation requires one realization per persona")
    return {
        "sequence_id": plan["sequence_id"],
        "candidate_id": generation["candidate_id"],
        "model_id": generation["model_id"],
        "language_code": generation["language_code"],
        "output_format": generation["output_format"],
        "apply_text_normalization": generation["apply_text_normalization"],
        "seed": generation["seed"],
        "inputs": inputs,
        "turns": turns,
    }


def voice_readiness_report(plan: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, str]] = []
    bindings: dict[str, dict[str, str]] = {}
    for character_id, persona in sorted(plan["_personas"].items()):
        voice = persona["voice"]
        active_id = voice.get("active_voice_realization_id")
        if not active_id:
            findings.append({
                "character_id": character_id,
                "code": "human_audition_pending",
                "message": "No human-approved active voice realization is selected.",
            })
            continue
        realization = next(
            item for item in voice["voice_realizations"]
            if item["voice_realization_id"] == active_id
        )
        audition_sha = realization["audition"]["audio_sha256"]
        expected = {
            "persona_version": persona["persona_version"],
            "voice_persona_id": voice["voice_persona_id"],
            "voice_realization_id": active_id,
            "audition_sha256": audition_sha,
        }
        bindings[character_id] = expected
        for beat in plan["beats"]:
            if beat.get("speaker") != character_id:
                continue
            binding = beat["voice_binding"]
            if any(binding.get(field) != value for field, value in expected.items()):
                findings.append({
                    "character_id": character_id,
                    "code": "dialogue_binding_not_active",
                    "message": f"{beat['dialogue_id']} is not bound to the active audition.",
                })
            master = plan["_performance_masters"][binding["performance_master_id"]]
            if (
                master.get("status") != "approved"
                or master.get("sha256") != audition_sha
                or master.get("audition_sha256") != audition_sha
            ):
                findings.append({
                    "character_id": character_id,
                    "code": "performance_master_not_approved",
                    "message": f"{master['performance_master_id']} is not the approved audition.",
                })
    return {
        "schema_version": SCHEMA_VERSION,
        "audit_type": "voice_persona_readiness",
        "sequence_id": plan["sequence_id"],
        "ready": not findings,
        "gate": "pass" if not findings else "block",
        "bindings": bindings,
        "findings": findings,
    }


def voice_budget_report(plan: dict[str, Any], config: Any) -> dict[str, Any]:
    """Recalculate the complete first-pass production cost from immutable inputs."""
    budget = plan.get("budget_plan_usd")
    if not isinstance(budget, dict):
        raise PolicyError("voice plan requires budget_plan_usd")
    hard_cap = Decimal(str(budget.get("hard_cap", "0")))
    repair_reserve = Decimal(str(budget.get("bounded_repair_reserve", "0")))
    nonproductive_reservations = Decimal(str(
        budget.get(
            "nonproductive_reservations",
            budget.get("nonproductive_voice_reservations", "0"),
        )
    ))
    historical_voice_spend = Decimal(str(
        budget.get("voice_auditions_successful_artifacts", "0")
    ))
    if (
        hard_cap <= 0 or repair_reserve < 0
        or nonproductive_reservations < 0 or historical_voice_spend < 0
    ):
        raise PolicyError("voice plan budget values are invalid")

    seconds_by_role: dict[str, int] = {}
    nonbillable_roles = {"deterministic_anchor_plate"}
    for beat in plan["beats"]:
        role = _require_string(beat, "model_role", f"beat {beat['beat_id']}")
        if role in nonbillable_roles:
            continue
        if role not in {"cosmos_world_video", "image_to_video"}:
            raise PolicyError(f"voice plan uses unsupported production role: {role}")
        seconds_by_role[role] = seconds_by_role.get(role, 0) + int(beat["seconds"])
    video_costs = {
        role: config.model(role).reserve(seconds=seconds)
        for role, seconds in sorted(seconds_by_role.items())
    }

    audition_costs: dict[str, Decimal] = {}
    for character_id, persona in sorted(plan["_personas"].items()):
        realization_ids = {
            beat["voice_binding"]["voice_realization_id"]
            for beat in plan["beats"] if beat.get("speaker") == character_id
        }
        realization_id = next(iter(realization_ids))
        realization = next(
            item for item in persona["voice"]["voice_realizations"]
            if item["voice_realization_id"] == realization_id
        )
        model = config.require_model(realization["model_id"])
        if model.role not in {"voice_design", "dialogue_voice"}:
            raise PolicyError("voice plan realization is not bound to an approved voice role")
        audition_costs[character_id] = model.reserve(
            characters=len(realization["audition"]["script"])
        )

    first_pass = sum(video_costs.values(), Decimal("0")) + sum(
        audition_costs.values(), Decimal("0")
    )
    maximum_planned = (
        first_pass + repair_reserve + nonproductive_reservations
        + historical_voice_spend
    )
    gate = "pass" if maximum_planned <= hard_cap else "block"
    return {
        "schema_version": SCHEMA_VERSION,
        "audit_type": "production_budget",
        "sequence_id": plan["sequence_id"],
        "hard_cap_usd": str(hard_cap),
        "video_seconds_by_role": seconds_by_role,
        "video_costs_usd": {key: str(value) for key, value in video_costs.items()},
        "voice_audition_costs_usd": {
            key: str(value) for key, value in audition_costs.items()
        },
        "first_pass_reserved_usd": str(first_pass),
        "historical_voice_spend_usd": str(historical_voice_spend),
        "nonproductive_reservations_usd": str(nonproductive_reservations),
        "bounded_repair_reserve_usd": str(repair_reserve),
        "maximum_planned_usd": str(maximum_planned),
        "remaining_to_hard_cap_usd": str(hard_cap - maximum_planned),
        "gate": gate,
    }
