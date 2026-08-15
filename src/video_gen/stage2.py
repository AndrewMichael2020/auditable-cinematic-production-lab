from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .errors import PolicyError
from .media import (mean_volume_dbfs, native_landscape_facts, probe, sha256_file)
from .voice import validate_voice_realization


SCHEMA_VERSION = "2.0"
ID_PATTERNS = {
    "series_id": re.compile(r"^ser-?[0-9a-z][0-9a-z-]*$"),
    "season_id": re.compile(r"^ssn-?[0-9a-z][0-9a-z-]*$"),
    "episode_id": re.compile(r"^ep-?[0-9a-z][0-9a-z-]*$"),
    "sequence_id": re.compile(r"^seq-?[0-9a-z][0-9a-z-]*$"),
    "scene_id": re.compile(r"^scn-?[0-9a-z][0-9a-z-]*$"),
    "setup_id": re.compile(r"^set-?[0-9a-z][0-9a-z-]*$"),
    "take_id": re.compile(r"^take-?[0-9a-z][0-9a-z-]*$"),
    "clip_id": re.compile(r"^clip-?[0-9a-z][0-9a-z-]*$"),
    "shot_id": re.compile(r"^shot-?[0-9a-z][0-9a-z-]*$"),
    "cut_id": re.compile(r"^cut-?[0-9a-z][0-9a-z-]*$"),
    "transition_id": re.compile(r"^trn-?[0-9a-z][0-9a-z-]*$"),
    "persona_version": re.compile(r"^pv[0-9]+$"),
}
HUMAN_GATES = (
    "cinematic_composition",
    "mouth_visibility",
    "lip_sync",
    "essential_action",
    "reference_fidelity",
    "functional_environment_logic",
    "anatomy_contact",
    "response_anticipation_eyeline",
    "motion_stability",
    "persona_voice",
    "ambient_audibility",
    "stitch_integrity",
)


def _load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _resolve(owner: Path, value: str) -> Path:
    candidate = Path(value)
    if candidate.is_file():
        return candidate
    return owner.parent / candidate


def _require_string(packet: dict[str, Any], field: str, context: str) -> str:
    value = str(packet.get(field, "")).strip()
    if not value:
        raise PolicyError(f"{context} requires {field}")
    return value


def _validate_typed_id(field: str, value: str) -> None:
    pattern = ID_PATTERNS.get(field)
    if pattern is not None and not pattern.fullmatch(value):
        raise PolicyError(f"invalid typed {field}: {value!r}")


def load_series(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    packet = _load(source)
    if packet.get("schema_version") != SCHEMA_VERSION:
        raise PolicyError("Stage 2 series manifest requires schema_version 2.0")
    series_id = _require_string(packet, "series_id", "series manifest")
    _validate_typed_id("series_id", series_id)
    for field in ("title", "premise", "style_bible"):
        _require_string(packet, field, "series manifest")
    cinematic = packet.get("cinematic_intent")
    if not isinstance(cinematic, dict):
        raise PolicyError("series manifest requires structured cinematic_intent")
    for field in ("dramatic_mode", "composition", "light", "colour", "performance", "exclusions"):
        _require_string(cinematic, field, "series cinematic_intent")
    personas = packet.get("canonical_personas")
    if not isinstance(personas, list) or not personas:
        raise PolicyError("series manifest requires canonical_personas")
    character_ids: set[str] = set()
    persona_ids: set[str] = set()
    voice_realization_ids: set[str] = set()
    for index, persona in enumerate(personas):
        if not isinstance(persona, dict):
            raise PolicyError(f"canonical persona {index} must be an object")
        context = f"canonical persona {index}"
        character_id = _require_string(persona, "character_id", context)
        persona_id = _require_string(persona, "persona_id", context)
        version = _require_string(persona, "persona_version", context)
        _validate_typed_id("persona_version", version)
        if character_id in character_ids or persona_id in persona_ids:
            raise PolicyError("canonical persona ids must be unique")
        character_ids.add(character_id)
        persona_ids.add(persona_id)
        for field in (
            "display_name", "age_baseline", "cultural_background", "local_history",
            "language_history", "accent", "appearance", "manner", "backstory",
        ):
            if field == "age_baseline":
                if int(persona.get(field, 0)) < 18:
                    raise PolicyError(f"{context} must be an adult")
            else:
                _require_string(persona, field, context)
        voice = persona.get("voice")
        if not isinstance(voice, dict):
            raise PolicyError(f"{context} requires a structured voice")
        for field in ("provider_voice", "language", "accent_direction", "performance_baseline"):
            _require_string(voice, field, f"{context} voice")
        if "voice_realization" in voice:
            realization = validate_voice_realization(
                voice["voice_realization"], persona_version=version,
            )
            realization_id = str(realization["voice_realization_id"])
            if realization_id in voice_realization_ids:
                raise PolicyError("canonical voice realization ids must be unique")
            voice_realization_ids.add(realization_id)
            if realization["provider_voice"] != voice["provider_voice"]:
                raise PolicyError(f"{context} voice realization conflicts with provider_voice")
            approval = realization["approval"]
            audition_path_value = str(approval.get("audition_path") or "").strip()
            if audition_path_value:
                audition_path = _resolve(source, audition_path_value)
                if not audition_path.is_file():
                    raise PolicyError(f"{context} voice audition does not exist")
                if sha256_file(audition_path) != approval["audition_sha256"]:
                    raise PolicyError(f"{context} voice audition hash does not match")
        else:
            # Stage 3 personas use a multi-candidate voice contract. Stage 2
            # validates its structure here without requiring unrelated audition
            # media; the dedicated voice-plan loader verifies those artifacts
            # before a Stage 3 candidate can be promoted.
            realizations = voice.get("voice_realizations")
            if not isinstance(realizations, list) or not realizations:
                raise PolicyError(f"{context} requires a canonical voice realization")
            candidate_ids: set[str] = set()
            for candidate in realizations:
                if not isinstance(candidate, dict):
                    raise PolicyError(f"{context} voice realization must be an object")
                candidate_id = _require_string(
                    candidate, "voice_realization_id", f"{context} voice realization"
                )
                if candidate_id in candidate_ids or candidate_id in voice_realization_ids:
                    raise PolicyError("canonical voice realization ids must be unique")
                candidate_ids.add(candidate_id)
                voice_realization_ids.add(candidate_id)
                if candidate.get("persona_version") != version:
                    raise PolicyError(f"{context} voice realization persona version is not canonical")
                for field in ("provider", "model_id", "model_version", "status"):
                    _require_string(candidate, field, f"{context} voice realization")
                settings = candidate.get("synthesis_settings")
                if not isinstance(settings, dict) or not settings:
                    raise PolicyError(f"{context} voice realization requires synthesis_settings")
                if any(
                    sensitive in str(key).lower()
                    for key in settings
                    for sensitive in ("token", "secret", "password", "api_key", "credential")
                ):
                    raise PolicyError(f"{context} voice realization settings contain credentials")
                if not isinstance(candidate.get("audition"), dict):
                    raise PolicyError(f"{context} voice realization requires an audition")
            active_id = voice.get("active_voice_realization_id")
            if active_id is not None:
                active = next(
                    (item for item in realizations
                     if item["voice_realization_id"] == active_id),
                    None,
                )
                if active is None or active.get("status") != "approved":
                    raise PolicyError(f"{context} active voice realization must be approved")
        reference_pack = persona.get("reference_pack")
        if not isinstance(reference_pack, dict):
            raise PolicyError(f"{context} requires a reference_pack")
        _require_string(reference_pack, "version", f"{context} reference_pack")
        visual_refs = reference_pack.get("visual_references")
        if not isinstance(visual_refs, list) or not visual_refs:
            raise PolicyError(f"{context} requires at least one planned visual reference")
    packet["_path"] = str(source)
    return packet


def load_stage2_sequence(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    packet = _load(source)
    if packet.get("schema_version") != SCHEMA_VERSION:
        raise PolicyError("Stage 2 sequence manifest requires schema_version 2.0")
    hierarchy = packet.get("hierarchy")
    if not isinstance(hierarchy, dict):
        raise PolicyError("Stage 2 sequence requires hierarchy")
    for field in ("series_id", "season_id", "episode_id", "sequence_id"):
        _validate_typed_id(field, _require_string(hierarchy, field, "hierarchy"))
    series_path = _resolve(source, _require_string(packet, "series_manifest", "sequence manifest"))
    if not series_path.is_file():
        raise PolicyError("series manifest does not exist")
    series = load_series(series_path)
    if series["series_id"] != hierarchy["series_id"]:
        raise PolicyError("sequence hierarchy series_id does not match the series manifest")
    prompt_policy_ref = packet.get("generation_prompt_policy")
    if not isinstance(prompt_policy_ref, dict):
        raise PolicyError("Stage 2 sequence requires generation_prompt_policy")
    prompt_policy_path = _resolve(
        source,
        _require_string(prompt_policy_ref, "source_path", "generation prompt policy"),
    )
    if not prompt_policy_path.is_file():
        raise PolicyError("generation prompt policy does not exist")
    if sha256_file(prompt_policy_path) != _require_string(
        prompt_policy_ref, "source_sha256", "generation prompt policy"
    ):
        raise PolicyError("generation prompt policy hash does not match")
    prompt_policy = _load(prompt_policy_path)
    if prompt_policy.get("schema_version") != "1.0":
        raise PolicyError("generation prompt policy requires schema_version 1.0")
    for field in (
        "policy_id", "functional_environment_clause_template",
        "response_anticipation_clause",
    ):
        _require_string(prompt_policy, field, "generation prompt policy")
    episode = packet.get("episode")
    if not isinstance(episode, dict):
        raise PolicyError("Stage 2 sequence requires episode state")
    _require_string(episode, "standalone_story", "episode state")
    states = episode.get("character_states")
    if not isinstance(states, list) or not states:
        raise PolicyError("episode state requires character_states")
    personas = {item["character_id"]: item for item in series["canonical_personas"]}
    state_ids: set[str] = set()
    for state in states:
        if not isinstance(state, dict):
            raise PolicyError("episode character state must be an object")
        character_id = _require_string(state, "character_id", "episode character state")
        if character_id not in personas or character_id in state_ids:
            raise PolicyError("episode character state must reference one unique series persona")
        state_ids.add(character_id)
        if state.get("persona_version") != personas[character_id]["persona_version"]:
            raise PolicyError("episode persona_version must match canonical series persona")
        for field in ("wardrobe", "knowledge", "objective", "emotional_state"):
            _require_string(state, field, "episode character state")
    reference = packet.get("reference_brief")
    if not isinstance(reference, dict):
        raise PolicyError("Stage 2 sequence requires reference_brief")
    source_image = _resolve(source, _require_string(reference, "source_path", "reference brief"))
    if not source_image.is_file():
        raise PolicyError("reference image does not exist")
    expected_hash = _require_string(reference, "source_sha256", "reference brief")
    if sha256_file(source_image) != expected_hash:
        raise PolicyError("reference image hash does not match the Stage 2 brief")
    anchors = reference.get("high_weight_anchors")
    minimum = int(reference.get("minimum_anchor_pass", 0))
    if not isinstance(anchors, list) or len(anchors) < 5 or not 4 <= minimum <= len(anchors):
        raise PolicyError("reference brief requires at least five anchors and a minimum pass of four")
    functional_checks = reference.get("functional_layout_checks")
    if (not isinstance(functional_checks, list) or len(functional_checks) < 3 or
            any(not str(item).strip() for item in functional_checks)):
        raise PolicyError("reference brief requires at least three functional_layout_checks")
    sound = packet.get("sound_plan")
    if not isinstance(sound, dict):
        raise PolicyError("Stage 2 sequence requires sound_plan")
    for field in ("ambience_kind", "opening_region", "pause_regions", "outro_region"):
        if not sound.get(field):
            raise PolicyError(f"sound_plan requires {field}")
    fade = float(sound.get("fade_seconds", 0))
    if not 0.25 <= fade <= 1.0:
        raise PolicyError("Stage 2 outer fade must be between 0.25 and 1.0 seconds")
    edit = packet.get("edit_policy")
    if not isinstance(edit, dict):
        raise PolicyError("Stage 2 sequence requires edit_policy")
    if edit.get("native_aspect_ratio") != "16:9" or edit.get("portrait_sources_allowed") is not False:
        raise PolicyError("Stage 2 edit policy must require native 16:9 and forbid portrait sources")
    if float(edit.get("intro_min_seconds", 0)) < 2 or float(edit.get("outro_min_seconds", 0)) < 3:
        raise PolicyError("Stage 2 edit policy requires a 2s intro and 3s outro minimum")
    if edit.get("freeze_holds_allowed") is not False or edit.get("imperceptible_stitches_required") is not True:
        raise PolicyError("Stage 2 edit policy must forbid freeze holds and require imperceptible stitches")
    scenes = packet.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise PolicyError("Stage 2 sequence requires at least one scene")
    all_shots: set[str] = set()
    all_setup_ids: set[str] = set()
    persona_ids = set(personas)
    for scene in scenes:
        if not isinstance(scene, dict):
            raise PolicyError("Stage 2 scene must be an object")
        scene_id = _require_string(scene, "scene_id", "Stage 2 scene")
        _validate_typed_id("scene_id", scene_id)
        _require_string(scene, "time", "Stage 2 scene")
        _require_string(scene, "place", "Stage 2 scene")
        setups = scene.get("setups")
        shots = scene.get("planned_shots")
        if not isinstance(setups, list) or not setups or not isinstance(shots, list) or not shots:
            raise PolicyError("each Stage 2 scene requires setups and planned_shots")
        setup_ids: set[str] = set()
        for setup in setups:
            setup_id = _require_string(setup, "setup_id", "setup")
            _validate_typed_id("setup_id", setup_id)
            if setup_id in setup_ids:
                raise PolicyError("setup ids must be unique within a scene")
            setup_ids.add(setup_id)
            if setup_id in all_setup_ids:
                raise PolicyError("setup ids must be unique within a sequence")
            all_setup_ids.add(setup_id)
            for field in ("camera_position", "camera_height", "lens_intent", "lighting", "axis"):
                _require_string(setup, field, "setup")
        for shot in shots:
            shot_id = _require_string(shot, "shot_id", "planned shot")
            _validate_typed_id("shot_id", shot_id)
            if shot_id in all_shots:
                raise PolicyError("shot ids must be unique within a sequence")
            all_shots.add(shot_id)
            if shot.get("setup_id") not in setup_ids:
                raise PolicyError("planned shot references an unknown setup")
            if shot.get("native_aspect_ratio") != "16:9":
                raise PolicyError("every Stage 2 planned shot must declare native 16:9")
            if shot.get("shot_size_class") not in {"wide", "medium", "close"}:
                raise PolicyError(
                    "every Stage 2 planned shot must classify shot size as wide, medium, or close"
                )
            for field in ("shot_size", "headroom", "look_room", "edit_purpose", "action"):
                _require_string(shot, field, "planned shot")
            if float(shot.get("seconds", 0)) <= 0:
                raise PolicyError("planned shot duration must be positive")
            visible_characters = shot.get("visible_characters")
            if (not isinstance(visible_characters, list) or not visible_characters or
                    len(visible_characters) != len(set(visible_characters)) or
                    not set(visible_characters) <= persona_ids):
                raise PolicyError(
                    "every Stage 2 shot requires unique visible_characters from series canon"
                )
            dialogue = shot.get("dialogue")
            dialogue_presentation = (
                str(dialogue.get("presentation", "onscreen"))
                if isinstance(dialogue, dict) else None
            )
            if dialogue and dialogue_presentation not in {"onscreen", "offscreen"}:
                raise PolicyError("dialogue presentation must be onscreen or offscreen")
            if (dialogue and dialogue_presentation == "onscreen" and
                    shot.get("mouth_visible_required") is not True):
                raise PolicyError("onscreen dialogue shots must require complete mouth visibility")
            if (dialogue and dialogue_presentation == "onscreen" and
                    dialogue.get("speaker") not in set(visible_characters)):
                raise PolicyError("onscreen dialogue speaker must be one of the visible characters")
            if (dialogue and dialogue_presentation == "onscreen" and
                    str(dialogue.get("line", "")).rstrip().endswith("?") and
                    shot.get("response_anticipation_required") is not True):
                raise PolicyError(
                    "question dialogue shots must require response anticipation eyeline"
                )
    source_takes = packet.get("planned_source_takes")
    if not isinstance(source_takes, list) or not 3 <= len(source_takes) <= 12:
        raise PolicyError("Stage 2 sequence requires three to twelve planned_source_takes")
    take_ids: set[str] = set()
    supported_shots: list[str] = []
    for take in source_takes:
        take_id = _require_string(take, "take_id", "planned source take")
        _validate_typed_id("take_id", take_id)
        if take_id in take_ids:
            raise PolicyError("planned source take ids must be unique")
        take_ids.add(take_id)
        if take.get("setup_id") not in all_setup_ids:
            raise PolicyError("planned source take references an unknown setup")
        if take.get("native_aspect_ratio") != "16:9":
            raise PolicyError("every planned source take must be native 16:9")
        visible = take.get("visible_characters")
        if (not isinstance(visible, list) or not visible or len(visible) != len(set(visible)) or
                not set(visible) <= persona_ids):
            raise PolicyError("planned source take has invalid visible_characters")
        supports = take.get("supports_shots")
        if not isinstance(supports, list) or not supports or not set(supports) <= all_shots:
            raise PolicyError("planned source take has invalid supports_shots")
        supported_shots.extend(supports)
        for field in ("framing", "action", "purpose"):
            _require_string(take, field, "planned source take")
    if sorted(supported_shots) != sorted(all_shots):
        raise PolicyError("planned source takes must cover every shot exactly once")
    action = packet.get("essential_action")
    if not isinstance(action, dict):
        raise PolicyError("Stage 2 sequence requires essential_action")
    for field in ("initiation", "contact_transfer", "completion"):
        _require_string(action, field, "essential action")
    packet["_path"] = str(source)
    packet["_series"] = series
    packet["_generation_prompt_policy"] = prompt_policy
    return packet


def compile_stage2_prompt(sequence: dict[str, Any], shot_id: str) -> str:
    """Compile one Stage 2 shot prompt from series persona and reference anchors."""
    shot = None
    setup = None
    for scene in sequence["scenes"]:
        shot = next((item for item in scene["planned_shots"] if item["shot_id"] == shot_id), None)
        if shot:
            setup = next(item for item in scene["setups"] if item["setup_id"] == shot["setup_id"])
            break
    if shot is None or setup is None:
        raise PolicyError(f"unknown Stage 2 shot: {shot_id}")
    series = sequence["_series"]
    personas = [
        item for item in series["canonical_personas"]
        if item["character_id"] in shot["visible_characters"]
    ]
    persona_text = "; ".join(
        f"{item['display_name']} ({item['cultural_background']}): {item['appearance']}; "
        f"stable manner {item['manner']}"
        for item in personas
    )
    anchors = "; ".join(sequence["reference_brief"]["high_weight_anchors"])
    functional = "; ".join(sequence["reference_brief"]["functional_layout_checks"])
    prompt_policy = sequence["_generation_prompt_policy"]
    functional_text = prompt_policy["functional_environment_clause_template"].format(
        requirements=functional
    )
    dialogue = shot.get("dialogue")
    dialogue_text = (
        f" {dialogue.get('presentation', 'onscreen').capitalize()} spoken line: {dialogue['line']}"
        if isinstance(dialogue, dict) else ""
    )
    anticipation_text = (
        f" {prompt_policy['response_anticipation_clause']}"
        if shot.get("response_anticipation_required") is True else ""
    )
    person_count = len(personas)
    count_direction = (
        "Exactly one foreground principal is visible; do not add another face, body, reflection, "
        "foreground shoulder or duplicate person. "
        if person_count == 1 else
        f"Exactly {person_count} foreground principals are visible, without duplicates or fused bodies. "
    )
    cinematic = series["cinematic_intent"]
    return (
        "Native cinematic 16:9 landscape, square pixels, high-production-value live-action narrative "
        f"cinema. Dramatic mode: {cinematic['dramatic_mode']} Composition: {cinematic['composition']} "
        f"Light: {cinematic['light']} Colour: {cinematic['colour']} Performance: "
        f"{cinematic['performance']} Exclude: {cinematic['exclusions']} "
        f"Reference environment anchors: {anchors}. Preserve these anchors as the dominant room design; "
        f"{functional_text} "
        "omit logos, facility names, readable signs, patient identifiers and readable monitor content. "
        f"{count_direction}Visible canonical principals: {persona_text}. Setup: camera {setup['camera_position']}, "
        f"height {setup['camera_height']}, lens {setup['lens_intent']}, lighting {setup['lighting']}, "
        f"axis {setup['axis']}. Shot: {shot['shot_size']}; headroom {shot['headroom']}; "
        f"look room {shot['look_room']}; action {shot['action']}; purpose {shot['edit_purpose']}. "
        "Keep complete forehead, eyes, nose, mouth, chin, jaw and shoulders safely framed. "
        "No portrait framing, pillarbox, blurred side fill, face-edge crop, camera gaze, malformed hands, "
        "badges, logos, lettering, generated words, or foreground obstruction of the speaking mouth."
        f"{dialogue_text}{anticipation_text}"
    )


def compile_stage2_take_prompt(sequence: dict[str, Any], take_id: str) -> str:
    """Compile one concise native-landscape source-take prompt with both principals in-world."""
    try:
        take = next(item for item in sequence["planned_source_takes"] if item["take_id"] == take_id)
    except StopIteration as exc:
        raise PolicyError(f"unknown Stage 2 source take: {take_id}") from exc
    setup = next(
        setup for scene in sequence["scenes"] for setup in scene["setups"]
        if setup["setup_id"] == take["setup_id"]
    )
    series = sequence["_series"]
    visible = set(take["visible_characters"])
    personas = [item for item in series["canonical_personas"] if item["character_id"] in visible]
    persona_text = "; ".join(
        f"{item['display_name']}: {item['appearance']} Wearing "
        f"{next(state['wardrobe'] for state in sequence['episode']['character_states'] if state['character_id'] == item['character_id'])}"
        for item in personas
    )
    anchors = "; ".join(sequence["reference_brief"]["high_weight_anchors"])
    functional = "; ".join(sequence["reference_brief"]["functional_layout_checks"])
    functional_text = sequence["_generation_prompt_policy"][
        "functional_environment_clause_template"
    ].format(requirements=functional)
    principal_direction = (
        "Generate the one canonical principal in this continuous scene"
        if len(personas) == 1 else
        "Generate both canonical principals together in the same continuous scene"
    )
    return (
        "Cinematic naturalistic drama, restrained feature-film realism, native 16:9 landscape. "
        "The image serves character, spatial clarity and dramatic behavior, with natural human skin, "
        "quiet micro-expression and no promotional performance. "
        f"Match this clinic environment closely: {anchors}. "
        f"{functional_text} "
        f"{principal_direction}: {persona_text}. "
        f"Camera: {setup['camera_position']}; {setup['camera_height']}; {setup['lens_intent']}; "
        f"{setup['lighting']}; axis: {setup['axis']}. Framing: {take['framing']}. "
        f"Action: {take['action']} Purpose: {take['purpose']}. "
        "Keep both complete faces, hair, mouths, chins, shoulders, hands and bodies safely composed. "
        "All surfaces remain plain and privacy-safe, without readable facility, card, monitor or clothing text."
    )


def _human_result(gate_id: str, raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        status, evidence = raw, ""
    elif isinstance(raw, dict):
        status = str(raw.get("status", "review"))
        evidence = str(raw.get("evidence", raw.get("observed_evidence", "")))
    else:
        status, evidence = "review", "No review supplied."
    if status not in {"pass", "fail", "review"}:
        status, evidence = "review", f"Invalid review status {status!r}."
    return {"gate_id": gate_id, "status": status, "evidence": evidence or "Reviewer decision."}


def audit_stage2_sequence(sequence: dict[str, Any], timeline: dict[str, Any], *,
                          final_media: str | Path | None = None,
                          observations: dict[str, Any] | None = None,
                          forbidden_generation_models: set[str] | None = None) -> dict[str, Any]:
    """Apply Stage 2 native-format, lineage, edit-rhythm, sound, and human gates."""
    observations = observations or {}
    forbidden_generation_models = forbidden_generation_models or {
        "FastVideo/FastWan-QAD-FP8-1.3B",
    }
    hierarchy = sequence["hierarchy"]
    intervals = timeline.get("intervals")
    results: list[dict[str, Any]] = []

    def add(gate_id: str, status: str, evidence: str) -> None:
        results.append({"gate_id": gate_id, "status": status, "evidence": evidence})

    unapproved_voices = []
    stage2_character_ids = {
        state["character_id"] for state in sequence["episode"]["character_states"]
    }
    for persona in sequence["_series"]["canonical_personas"]:
        if persona["character_id"] not in stage2_character_ids:
            continue
        realization = persona["voice"].get("voice_realization")
        if realization is None:
            unapproved_voices.append(
                f"{persona['character_id']} has no Stage 2 voice realization"
            )
            continue
        if realization["approval"]["status"] != "approved":
            unapproved_voices.append(
                f"{persona['character_id']}={realization['voice_realization_id']} "
                f"({realization['approval']['status']})"
            )
    if unapproved_voices:
        add(
            "voice_realization", "fail",
            "Production promotion requires approved audition bindings: "
            + "; ".join(unapproved_voices) + ".",
        )
    else:
        add(
            "voice_realization", "pass",
            "Every Stage 2 speaker resolves to one human-approved audition hash.",
        )

    if not isinstance(intervals, list) or not intervals:
        add("timeline", "fail", "Timeline has no intervals.")
        intervals = []
    selected_durations: list[float] = []
    for index, interval in enumerate(intervals):
        required = {
            "series_id", "season_id", "episode_id", "sequence_id", "scene_id", "setup_id",
            "take_id", "clip_id", "shot_id", "transition_after", "generation_source_path",
            "generation_request_id", "generation_model_id", "persona_versions", "transition_id",
            "cut_after_id",
            "path", "start", "end",
        }
        missing = required - interval.keys()
        if missing:
            add("typed_lineage", "fail",
                f"Interval {index} missing {', '.join(sorted(missing))}.")
        for field in ("series_id", "season_id", "episode_id", "sequence_id"):
            if interval.get(field) != hierarchy.get(field):
                add("typed_lineage", "fail", f"Interval {index} {field} does not match hierarchy.")
        for field in ("scene_id", "setup_id", "take_id", "clip_id", "shot_id"):
            value = str(interval.get(field, ""))
            if not ID_PATTERNS[field].fullmatch(value):
                add("typed_lineage", "fail", f"Interval {index} has invalid {field}={value!r}.")
        transition_id = str(interval.get("transition_id", ""))
        if not ID_PATTERNS["transition_id"].fullmatch(transition_id):
            add("typed_lineage", "fail", f"Interval {index} has invalid transition_id.")
        cut_after_id = interval.get("cut_after_id")
        if interval.get("transition_after") == "cut":
            if not ID_PATTERNS["cut_id"].fullmatch(str(cut_after_id or "")):
                add("typed_lineage", "fail", f"Interval {index} cut lacks a typed cut_after_id.")
        elif cut_after_id is not None:
            add("typed_lineage", "fail", f"Interval {index} non-cut transition has cut_after_id.")
        if not str(interval.get("generation_request_id", "")).strip():
            add("typed_lineage", "fail", f"Interval {index} lacks generation_request_id.")
        generation_model_id = str(interval.get("generation_model_id", ""))
        if generation_model_id in forbidden_generation_models:
            add(
                "cinematic_source_model", "fail",
                f"Interval {index} uses quarantined non-cinematic model {generation_model_id}.",
            )
        shot_personas: dict[str, str] = {}
        shot_id = interval.get("shot_id")
        for scene in sequence["scenes"]:
            planned = next(
                (item for item in scene["planned_shots"] if item["shot_id"] == shot_id), None,
            )
            if planned:
                canonical = {
                    item["character_id"]: item["persona_version"]
                    for item in sequence["_series"]["canonical_personas"]
                }
                shot_personas = {
                    character_id: canonical[character_id]
                    for character_id in planned["visible_characters"]
                }
                break
        if interval.get("persona_versions") != shot_personas:
            add(
                "typed_lineage", "fail",
                f"Interval {index} persona_versions do not match the planned canonical versions.",
            )
        path = Path(str(interval.get("path", "")))
        generation_source_value = str(interval.get("generation_source_path", ""))
        generation_source = Path(generation_source_value) if generation_source_value else None
        if generation_source is None or not generation_source.is_file():
            add("native_origin", "fail", f"Interval {index} has no existing generation source.")
        else:
            generation_facts = native_landscape_facts(generation_source)
            if not generation_facts["native_landscape_16_9"]:
                square_exception = (
                    interval.get("source_role") == "dialogue_turn"
                    and interval.get("performance_source_exception")
                    == "approved_square_avatar_performance"
                    and generation_facts["width"] == generation_facts["height"]
                    and generation_facts["sample_aspect_ratio"] in {"1:1", "0:1", "N/A"}
                )
                reference_origin = Path(str(interval.get("generation_reference_origin_path", "")))
                crop = interval.get("generation_crop")
                crop_valid = False
                if isinstance(crop, dict):
                    try:
                        crop_width = int(crop["width"])
                        crop_height = int(crop["height"])
                        crop_x = int(crop["x"])
                        crop_y = int(crop["y"])
                        crop_valid = (
                            crop_width * 9 == crop_height * 16
                            and crop_width >= generation_facts["width"] * 0.75
                            and crop_height >= generation_facts["height"] * 0.45
                            and crop_x >= 0 and crop_y >= 0
                            and crop_x + crop_width <= generation_facts["width"]
                            and crop_y + crop_height <= generation_facts["height"]
                        )
                    except (KeyError, TypeError, ValueError):
                        crop_valid = False
                reference_valid = (
                    reference_origin.is_file()
                    and native_landscape_facts(reference_origin)["native_landscape_16_9"]
                )
                if not (square_exception and reference_valid and crop_valid):
                    add(
                        "native_origin", "fail",
                        f"Interval {index} generation source is {generation_facts['width']}x"
                        f"{generation_facts['height']} SAR {generation_facts['sample_aspect_ratio']} "
                        "without a complete approved square-avatar performance exception.",
                    )
        if not path.is_file():
            add("source_exists", "fail", f"Interval {index} source does not exist: {path}.")
            continue
        facts = native_landscape_facts(path)
        if not facts["native_landscape_16_9"]:
            add("native_format", "fail",
                f"Interval {index} is {facts['width']}x{facts['height']} SAR {facts['sample_aspect_ratio']}.")
        if float(interval.get("hold_after", 0)) != 0:
            add("freeze_hold", "fail", f"Interval {index} uses a freeze hold.")
        transition = interval.get("transition_after")
        if transition not in {"cut", "fade_out", "none", "stitch"}:
            add("transition", "fail", f"Interval {index} has invalid transition {transition!r}.")
        if transition == "stitch" and interval.get("stitch_audit") != "pass":
            add("stitch", "fail", f"Interval {index} uses an unaudited stitch.")
        try:
            selected_durations.append(
                (float(interval["end"]) - float(interval["start"])) /
                float(interval.get("rate", 1.0))
            )
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            add("timeline", "fail", f"Interval {index} has invalid edit bounds.")
    if intervals:
        first_duration = selected_durations[0] if selected_durations else 0.0
        last_duration = selected_durations[-1] if selected_durations else 0.0
        if intervals[0].get("source_role") != "opening_master" or first_duration < 2.0:
            add("intro", "fail", "Opening must be a readable master lasting at least 2 seconds.")
        if intervals[-1].get("source_role") != "outro_reaction" or last_duration < 3.0:
            add("outro", "fail", "Outro must be a living reaction lasting at least 3 seconds.")
        if intervals[-1].get("transition_after") != "fade_out":
            add("outer_fade", "fail", "Last interval must end with the planned fade-out.")
    ambience = timeline.get("ambience")
    if not ambience or not Path(str(ambience)).is_file():
        add("ambience", "fail", "Timeline requires an existing location ambience bed.")
    if not any(item["status"] == "fail" and item["gate_id"] == "native_format" for item in results):
        add("native_format", "pass", "Every existing timeline source is native square-pixel 16:9 landscape.")
    if not any(item["status"] == "fail" and item["gate_id"] == "native_origin" for item in results):
        add("native_origin", "pass", "Every interval originates from native square-pixel 16:9 generation.")
    if not any(item["status"] == "fail" and item["gate_id"] == "cinematic_source_model" for item in results):
        add("cinematic_source_model", "pass", "No interval uses a quarantined non-cinematic model.")
    if not any(item["status"] == "fail" and item["gate_id"] == "typed_lineage" for item in results):
        add("typed_lineage", "pass", "Every interval has typed production and edit lineage.")
    if final_media is not None:
        final_path = Path(final_media)
        if not final_path.is_file():
            add("delivery_master", "fail", "Delivery master does not exist.")
        else:
            facts = native_landscape_facts(final_path)
            if not facts["native_landscape_16_9"]:
                add("delivery_master", "fail", "Delivery master is not native square-pixel 16:9.")
            else:
                duration = float(probe(final_path).get("format", {}).get("duration", 0))
                intro_mean = mean_volume_dbfs(final_path, start=0, duration=min(3.0, duration))
                outro_duration = min(3.0, duration)
                outro_mean = mean_volume_dbfs(
                    final_path, start=max(0.0, duration - outro_duration), duration=outro_duration,
                )
                status = "pass" if intro_mean >= -50 and outro_mean >= -50 else "fail"
                add("ambience_level", status,
                    f"Intro mean {intro_mean:.1f} dBFS; outro mean {outro_mean:.1f} dBFS.")
    for gate_id in HUMAN_GATES:
        results.append(_human_result(gate_id, observations.get(gate_id)))
    blocked = any(item["status"] == "fail" for item in results)
    review = any(item["status"] == "review" for item in results)
    return {
        "schema_version": SCHEMA_VERSION,
        "audit_type": "stage2_sequence",
        "hierarchy": hierarchy,
        "sequence_manifest": sequence.get("_path"),
        "results": results,
        "blocking_findings": sum(item["status"] == "fail" for item in results),
        "review_findings": sum(item["status"] == "review" for item in results),
        "promotion_allowed": not blocked and not review,
        "gate": "block" if blocked else ("review" if review else "pass"),
    }
