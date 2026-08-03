from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .media import probe, sha256_file
from .production import (compile_prompt, location_profile_for_scene,
                         principal_characters)


SCHEMA_VERSION = "2.0"
AUDIT_STAGES = (
    "storyboard",
    "cheap_draft",
    "final_candidate",
    "cross_shot_continuity",
    "cross_scene_continuity",
    "final_sequence",
)
NEXT_STAGE = {
    "storyboard": "cheap_draft",
    "cheap_draft": "final_candidate",
    "final_candidate": "cross_shot_continuity",
    "cross_shot_continuity": "cross_scene_continuity",
    "cross_scene_continuity": "final_sequence",
    "final_sequence": "final",
}
TEXT_BEARING_TERMS = (
    "advertisement", "caption", "label", "lettering", "menu", "poster",
    "sign", "signage", "subtitle", "timetable", "writing",
)
LEGACY_SAFE_ZONES = {
    "left_safe_zone": -2,
    "center_left_safe_zone": -1,
    "center_safe_zone": 0,
    "center_right_safe_zone": 1,
    "right_safe_zone": 2,
    "off_screen_left": -3,
    "off_screen_right": 3,
}
PLAUSIBLE_SUPPORTS = {
    "ground", "floor", "wall", "wall_mounted", "post_mounted", "ceiling_mounted",
    "structure_mounted", "counter", "countertop", "desk", "desk_mounted", "built_in",
}
BASE_RULES: dict[str, dict[str, Any]] = {
    "technical_validity": {"label": "Technical validity", "severity": "block",
                           "expected": "Media decodes with the planned duration and required streams."},
    "room_geometry": {"label": "Room geometry", "severity": "block",
                      "expected": "Walls, counters, chairs, workstations, floors, and camera can physically coexist."},
    "circulation": {"label": "Circulation", "severity": "block",
                    "expected": "Declared movement paths remain safe, visible, and unobstructed."},
    "spatial_anchors": {"label": "Spatial anchors", "severity": "block",
                        "expected": "Doors, walls, counters, windows, seating, and workstations remain stable."},
    "master_coverage": {"label": "Master and coverage", "severity": "block",
                        "expected": "A wide master establishes geography that all closer coverage preserves."},
    "character_count_identity": {"label": "Character count and identity", "severity": "block",
                                 "expected": "Speaking principals remain identifiable and no person is duplicated or fused."},
    "background_population": {"label": "Background population", "severity": "block",
                              "expected": "Occupancy and crowd placement stay within the planned range."},
    "crowd_continuity": {"label": "Crowd continuity", "severity": "block",
                         "expected": "Background people do not abruptly duplicate, disappear, intersect objects, or stare at the action."},
    "blocking_and_framing": {"label": "Blocking and framing", "severity": "block",
                             "expected": "Positions, scale, screen direction, and framing follow the shot plan."},
    "gaze_and_eyeline": {"label": "Gaze and eyeline", "severity": "block",
                         "expected": "Actors look at planned story targets and never into the camera."},
    "anatomy_contact": {"label": "Anatomy and contact", "severity": "block",
                        "expected": "Hands, feet, limbs, body contact, and object contact are plausible."},
    "wardrobe_construction": {"label": "Wardrobe construction", "severity": "block",
                              "expected": "Buttons, pockets, sleeves, closures, and accessories remain coherent."},
    "prop_identity_ownership": {"label": "Prop identity and ownership", "severity": "block",
                                "expected": "Props keep their shape, colour, owner, and planned location."},
    "prop_interaction": {"label": "Prop interaction", "severity": "block",
                         "expected": "Handoffs and manipulation preserve physical contact and object identity."},
    "privacy": {"label": "Privacy", "severity": "block",
                "expected": "Protected identifiers, card faces, and monitor content remain unreadable."},
    "unwanted_text": {"label": "Unwanted text", "severity": "block",
                      "expected": "No malformed or unnecessary words, letters, numbers, signs, captions, or watermarks appear."},
    "lighting_continuity": {"label": "Lighting continuity", "severity": "block",
                            "expected": "Light direction, colour, and time of day remain coherent."},
    "performance_action_match": {"label": "Performance and action", "severity": "review",
                                 "expected": "Facial performance and physical action fit the dialogue and dramatic beat."},
    "audio_sync": {"label": "Audio and lip sync", "severity": "block",
                   "expected": "Dialogue audio remains synchronized with its generated picture."},
    "continuity": {"label": "Continuity", "severity": "block",
                   "expected": "Faces, wardrobe, location, props, narrative facts, and screen direction remain stable."},
    "symbolic_environment": {"label": "Symbolic environment", "severity": "review",
                             "expected": "Meaning comes from restrained light, colour, distance, architecture, and sparse text-free symbols."},
}
DRAFT_CRITERIA = tuple(
    (rule_id, value["label"], value["expected"]) for rule_id, value in BASE_RULES.items()
    if rule_id != "technical_validity"
)


def canonical_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(data).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _result(*, stage: str, scene_id: str | None, shot_id: str | None, rule_id: str,
            status: str, confidence: float, evidence: str, expected: str | None = None,
            severity: str | None = None, repair: str = "Review the protected plan and repair only this defect.",
            protected: list[str] | None = None, next_stage: str | None = None) -> dict[str, Any]:
    catalog = BASE_RULES.get(rule_id, {})
    severity = severity or str(catalog.get("severity", "block"))
    expected = expected or str(catalog.get("expected", "The declared production constraint is satisfied."))
    promotion_blocked = status == "review" or (status == "fail" and severity == "block")
    if status == "fail" and severity != "block":
        status = "review"
        promotion_blocked = True
    return {
        "audit_stage": stage,
        "scene_id": scene_id,
        "shot_id": shot_id,
        "rule_id": rule_id,
        "severity": severity,
        "confidence": round(max(0.0, min(float(confidence), 1.0)), 3),
        "observed_evidence": evidence,
        "expected_condition": expected,
        "status": status,
        "promotion_blocked": promotion_blocked,
        "recommended_repair_action": "none" if status == "pass" else repair,
        "protected_constraints": protected or [],
        "suggested_next_pipeline_stage": (
            next_stage or (NEXT_STAGE.get(stage, "human_review") if status == "pass" else
                           ("human_review" if status == "review" else stage))
        ),
    }


def _get_path(value: dict[str, Any], dotted: str) -> Any:
    current: Any = value
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _custom_rule_passes(actual: Any, rule: dict[str, Any]) -> bool:
    operator = rule.get("operator", "equals")
    expected = rule.get("value")
    if operator == "equals":
        return actual == expected
    if operator == "one_of":
        return actual in rule.get("values", [])
    if operator == "min":
        return isinstance(actual, (int, float)) and actual >= expected
    if operator == "between":
        bounds = rule.get("values", [])
        return (isinstance(actual, (int, float)) and len(bounds) == 2 and
                bounds[0] <= actual <= bounds[1])
    if operator == "nonempty":
        return bool(actual)
    return False


def _zone_positions(scene: dict[str, Any], profile: dict[str, Any] | None) -> dict[str, float]:
    if profile:
        values = {
            str(item["id"]): float(item.get("screen_position", 0))
            for item in profile.get("zones", []) if isinstance(item, dict) and item.get("id")
        }
        values.update({"off_screen_left": -99.0, "off_screen_right": 99.0})
        return values
    return dict(LEGACY_SAFE_ZONES)


def _rule_catalog(scene: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = dict(BASE_RULES)
    profile = location_profile_for_scene(scene)
    for item in (profile or {}).get("validation_rules", []):
        result[str(item["rule_id"])] = {
            "label": item.get("label", item["rule_id"]),
            "severity": item.get("severity", "block"),
            "expected": item.get("expected_condition", "The location-specific requirement is satisfied."),
        }
    return result


def audit_scene(scene: dict[str, Any]) -> dict[str, Any]:
    """Reusable pre-generation storyboard, prompt, spatial, privacy, and continuity gate."""
    stage = "storyboard"
    scene_id = scene.get("id")
    results: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    visual = scene.get("visual_policy") if isinstance(scene.get("visual_policy"), dict) else {}
    spatial = scene.get("spatial_plan") if isinstance(scene.get("spatial_plan"), dict) else {}
    profile = location_profile_for_scene(scene)
    characters = principal_characters(scene)
    character_ids = {str(item.get("id")) for item in characters}
    zones = _zone_positions(scene, profile)

    def fail(code: str, path: str, evidence: str, expected: str, *, rule_id: str | None = None,
             severity: str = "block", shot_id: str | None = None, repair: str,
             protected: list[str] | None = None) -> None:
        result = _result(stage=stage, scene_id=scene_id, shot_id=shot_id,
                         rule_id=rule_id or code, status="fail", confidence=1.0,
                         evidence=evidence, expected=expected, severity=severity,
                         repair=repair, protected=protected)
        results.append(result)
        findings.append({"severity": "block" if result["promotion_blocked"] else severity,
                         "code": code, "path": path, "message": evidence})

    if not visual:
        fail("missing_visual_policy", "visual_policy", "Structured visual policy is absent.",
             "Every scene declares text, camera-gaze, and symbolic-environment policy.",
             rule_id="unwanted_text", repair="Add a structured visual_policy before generation.")
    text_policy = visual.get("text_policy")
    if text_policy not in {"forbid", "essential_only"}:
        fail("invalid_text_policy", "visual_policy.text_policy", f"Observed {text_policy!r}.",
             "text_policy is forbid or essential_only.", rule_id="unwanted_text",
             repair="Choose a supported text policy.")
    if text_policy == "forbid":
        location_text = " ".join(str(scene.get("location", {}).get(field, ""))
                                 for field in ("name", "layout", "light")).lower()
        for term in TEXT_BEARING_TERMS:
            if term in location_text:
                fail("text_environment_conflict", "location.layout",
                     f"No-text policy conflicts with location term {term!r}.",
                     "The location plan does not require a text-bearing object.",
                     rule_id="unwanted_text", repair="Remove the text-bearing design requirement.",
                     protected=["no readable generated text"])
    symbols = visual.get("public_space_symbols", {})
    if (not isinstance(symbols, dict) or not isinstance(symbols.get("max_icons"), int) or
            not 0 <= symbols.get("max_icons", -1) <= 2):
        fail("icon_density", "visual_policy.public_space_symbols", "Sparse icon limit is invalid.",
             "Public-space max_icons is an integer from zero to two.", rule_id="symbolic_environment",
             severity="review", repair="Set a bounded sparse icon policy.")
    metaphors = visual.get("environmental_metaphors", [])
    if not isinstance(metaphors, list) or not 1 <= len(metaphors) <= 4:
        fail("environmental_metaphor_density", "visual_policy.environmental_metaphors",
             "Environmental metaphor plan is missing or excessive.",
             "Use one to four restrained environmental metaphors.", rule_id="symbolic_environment",
             severity="review", repair="Keep only the essential light, colour, distance, or architecture cues.")
    if visual.get("camera_gaze_policy") != "never_look_at_camera":
        fail("camera_gaze_policy", "visual_policy.camera_gaze_policy",
             "Direct camera gaze is not explicitly forbidden.",
             "Every actor is forbidden from looking into the camera.", rule_id="gaze_and_eyeline",
             repair="Set camera_gaze_policy to never_look_at_camera.",
             protected=["camera remains an unnoticed observer"])

    anchors = (profile or {}).get("anchors", spatial.get("objects", []))
    if not isinstance(anchors, list) or not anchors:
        fail("missing_object_anchors", "spatial_plan.objects", "No stable spatial anchors are declared.",
             "At least one supported environmental anchor is declared.", rule_id="spatial_anchors",
             repair="Declare the minimum stable walls, counter, seating, or other anchors.")
        anchors = []
    seen_anchors: set[str] = set()
    for index, item in enumerate(anchors):
        path = f"anchors[{index}]"
        if not isinstance(item, dict):
            fail("invalid_object_anchor", path, "Anchor is not structured.",
                 "Each anchor has an id, zone, and support.", rule_id="spatial_anchors",
                 repair="Replace it with a structured anchor record.")
            continue
        anchor_id = str(item.get("id", ""))
        if not anchor_id or anchor_id in seen_anchors:
            fail("duplicate_object_anchor", f"{path}.id", f"Invalid anchor id {anchor_id!r}.",
                 "Anchor ids are unique and non-empty.", rule_id="spatial_anchors",
                 repair="Assign a stable unique anchor id.")
        seen_anchors.add(anchor_id)
        if item.get("support") not in PLAUSIBLE_SUPPORTS:
            fail("implausible_object_support", f"{path}.support",
                 f"Anchor {anchor_id!r} lacks plausible support.",
                 "Every object declares a physically plausible support.", rule_id="room_geometry",
                 repair="Declare how this object contacts the floor, wall, ceiling, counter, or desk.")
        if text_policy == "forbid" and item.get("contains_text") is not False:
            fail("text_bearing_object", f"{path}.contains_text", f"Anchor {anchor_id!r} may contain text.",
                 "All planned visible anchors explicitly contain no text.", rule_id="unwanted_text",
                 repair="Remove text or mark the surface plain and unreadable.")

        # Backward-compatible platform rules remain isolated from generic and profile-driven checks.
        if profile is None and item.get("kind") == "bench":
            if not isinstance(item.get("minimum_edge_distance_m"), (int, float)) or item["minimum_edge_distance_m"] < 2:
                fail("unsafe_bench_placement", f"{path}.minimum_edge_distance_m",
                     "Bench clearance from the platform edge is unsafe.",
                     "Bench is at least two metres from the edge.", rule_id="circulation",
                     repair="Move the bench into the far safe zone.")
            if item.get("orientation") != "parallel_to_tracks":
                fail("bench_orientation", f"{path}.orientation", "Bench orientation conflicts with the tracks.",
                     "Bench remains parallel to the tracks.", rule_id="room_geometry",
                     repair="Align the bench with the declared platform geometry.")
        if profile is None and item.get("kind") == "lamp" and item.get("support") not in {"wall_mounted", "post_mounted"}:
            fail("public_lamp_mounting", f"{path}.support", "Outdoor lamp mounting is implausible.",
                 "Platform lamp is wall- or post-mounted.", rule_id="room_geometry",
                 repair="Use a wall- or post-mounted public fixture.")

    if profile:
        circulation = profile.get("circulation_paths", [])
        if not circulation:
            fail("missing_circulation", "location_profile.circulation_paths",
                 "No circulation path is declared.", "At least one safe movement path is declared.",
                 rule_id="circulation", repair="Declare entry, waiting, counter, and exit paths.")
        for index, path in enumerate(circulation):
            if (not isinstance(path, dict) or path.get("blocked") is not False or
                    float(path.get("minimum_width_m", 0)) < 0.9):
                fail("blocked_circulation", f"location_profile.circulation_paths[{index}]",
                     "A circulation path is blocked or too narrow.",
                     "Every path is unblocked and at least 0.9 metres wide.", rule_id="circulation",
                     repair="Widen or reroute the declared circulation path.")
        for custom in profile.get("validation_rules", []):
            actual = _get_path({"scene": scene, "profile": profile}, str(custom.get("field", "")))
            if not _custom_rule_passes(actual, custom):
                fail(str(custom["rule_id"]), str(custom.get("field", "")),
                     f"Observed {actual!r}.", str(custom.get("expected_condition", "Location requirement must pass.")),
                     severity=str(custom.get("severity", "block")),
                     repair=str(custom.get("recommended_repair_action", "Repair this location-specific plan field.")),
                     protected=list(custom.get("protected_constraints", [])))

    background = scene.get("background_population", {})
    if background:
        minimum = int(background.get("minimum_adults", -1))
        target = int(background.get("target_adults", -1))
        maximum = int(background.get("maximum_adults", -1))
        occupancy = float(background.get("target_occupancy", -1))
        if not 0 <= minimum <= target <= maximum or not 0 <= occupancy <= 1:
            fail("background_population_plan", "background_population",
                 "Background count or occupancy bounds are incoherent.",
                 "Counts are ordered and target occupancy is between zero and one.",
                 rule_id="background_population", repair="Correct the count range and occupancy target.")

    for index, character in enumerate(characters):
        checks = character.get("wardrobe_visual") if isinstance(character, dict) else None
        if not isinstance(checks, list) or not checks:
            fail("missing_wardrobe_construction", f"principal_characters[{index}].wardrobe_visual",
                 f"{character.get('id')} lacks garment construction anchors.",
                 "Every principal has structured wardrobe construction.", rule_id="wardrobe_construction",
                 repair="Declare stable garment, colour, closure, pocket, sleeve, and accessory anchors.")

    privacy_props = {str(item.get("id")): item for item in scene.get("props", [])
                     if isinstance(item, dict) and item.get("privacy_sensitive") is True}
    for prop_id, item in privacy_props.items():
        states = item.get("allowed_visibility_states", [])
        if not states or not set(states).issubset({"face_down", "edge_on", "occluded", "in_motion", "out_of_focus"}):
            fail("privacy_prop_states", f"props.{prop_id}.allowed_visibility_states",
                 f"Privacy-sensitive prop {prop_id!r} lacks a safe visibility-state allowlist.",
                 "Privacy-sensitive props use only face-down, edge-on, occluded, in-motion, or out-of-focus states.",
                 rule_id="privacy", repair="Declare only safe unreadable visibility states.",
                 protected=["no personal identifier", "no readable card or monitor"])

    master_shots = 0
    for index, shot in enumerate(scene.get("shots", [])):
        path = f"shots[{index}]"
        shot_id = shot.get("id")
        if shot.get("spatial_role") == "master":
            master_shots += 1
            if shot.get("camera", {}).get("framing") not in {"wide_master", "wide_full_body"}:
                fail("invalid_master_framing", f"{path}.camera.framing",
                     "Master shot is not wide enough to prove geography.",
                     "Master uses a wide establishing framing.", rule_id="master_coverage",
                     shot_id=shot_id, repair="Widen the master to include anchors, principals, and circulation.")
        blocking = shot.get("blocking") if isinstance(shot, dict) else None
        if not isinstance(blocking, dict):
            fail("missing_blocking", f"{path}.blocking", "Shot has no structured blocking.",
                 "Every shot locates both principals.", rule_id="blocking_and_framing",
                 shot_id=shot_id, repair="Add start and end zones for both principals.")
            continue
        if set(blocking) - {"minimum_separation_m"} != character_ids:
            fail("blocking_characters", f"{path}.blocking", "Blocking does not name exactly both principals.",
                 "Blocking names every and only speaking principal.", rule_id="blocking_and_framing",
                 shot_id=shot_id, repair="Correct the principal ids in the blocking record.")
        for character_id in character_ids:
            movement = blocking.get(character_id, {})
            for endpoint in ("start", "end"):
                if not isinstance(movement, dict) or movement.get(endpoint) not in zones:
                    fail("unsafe_character_zone", f"{path}.blocking.{character_id}.{endpoint}",
                         f"{character_id} uses an undeclared {endpoint} zone.",
                         "Principal positions use a declared location zone.", rule_id="blocking_and_framing",
                         shot_id=shot_id, repair="Move the principal to a declared safe zone.")
        if not isinstance(blocking.get("minimum_separation_m"), (int, float)) or blocking["minimum_separation_m"] < 0.5:
            fail("character_separation", f"{path}.blocking.minimum_separation_m",
                 "Principal separation is missing or implausibly small.",
                 "Principals maintain at least 0.5 metres unless a planned handoff explicitly closes the gap.",
                 rule_id="room_geometry", shot_id=shot_id,
                 repair="Increase separation or explicitly plan the handoff contact zone.")
        gaze = shot.get("gaze")
        if not isinstance(gaze, dict) or set(gaze) != character_ids:
            fail("missing_gaze_plan", f"{path}.gaze", "Shot does not define gaze for both principals.",
                 "Every principal has a target and screen direction.", rule_id="gaze_and_eyeline",
                 shot_id=shot_id, repair="Add a complete two-principal gaze map.")
            continue
        for character_id in character_ids:
            instruction = gaze.get(character_id, {})
            target = instruction.get("target") if isinstance(instruction, dict) else None
            direction = instruction.get("screen_direction") if isinstance(instruction, dict) else None
            if target == "camera" or instruction.get("camera_look_forbidden") is not True:
                fail("camera_look", f"{path}.gaze.{character_id}",
                     f"{character_id} is not explicitly barred from lens contact.",
                     "Camera gaze is forbidden in every shot.", rule_id="gaze_and_eyeline",
                     shot_id=shot_id, repair="Target the scene partner, prop, or workstation; forbid camera gaze.",
                     protected=["no actor looks into camera"])
            if direction not in {"screen_left", "screen_right", "down"}:
                fail("invalid_eyeline_direction", f"{path}.gaze.{character_id}.screen_direction",
                     f"Invalid direction {direction!r}.", "Direction is screen_left, screen_right, or down.",
                     rule_id="gaze_and_eyeline", shot_id=shot_id,
                     repair="Choose the direction implied by blocking and target position.")
            if target in character_ids and target != character_id:
                actor_zone = blocking.get(character_id, {}).get("end")
                target_zone = blocking.get(target, {}).get("end")
                if actor_zone in zones and target_zone in zones:
                    expected_direction = "screen_right" if zones[target_zone] > zones[actor_zone] else "screen_left"
                    if direction != expected_direction:
                        fail("eyeline_axis_conflict", f"{path}.gaze.{character_id}.screen_direction",
                             f"{character_id} should look {expected_direction} toward {target}.",
                             "Eyeline direction follows the declared screen positions.", rule_id="gaze_and_eyeline",
                             shot_id=shot_id, repair="Correct the eyeline without crossing the camera axis.")
        for prop_id in shot.get("privacy_props_visible", []):
            prop = privacy_props.get(prop_id)
            state = shot.get("prop_visibility", {}).get(prop_id)
            if prop is None or state not in prop.get("allowed_visibility_states", []):
                fail("privacy_prop_exposure", f"{path}.prop_visibility.{prop_id}",
                     f"Protected prop {prop_id!r} uses unsafe or undeclared state {state!r}.",
                     "Every visible privacy prop uses its safe unreadable state allowlist.",
                     rule_id="privacy", shot_id=shot_id,
                     repair="Make the prop face-down, edge-on, occluded, moving, or out of focus.",
                     protected=["no personal identifier", "no readable card face"])

    if master_shots < 1:
        fail("missing_master_shot", "shots", "No wide master establishes the room and scene axis.",
             "At least one wide master establishes principals, anchors, occupancy, and circulation.",
             rule_id="master_coverage", repair="Add a geography-establishing wide master.")

    if profile is None and spatial.get("platform"):
        platform = spatial["platform"]
        if platform.get("tracks_relation") != "beyond_platform_edge":
            fail("ambiguous_track_geometry", "spatial_plan.platform.tracks_relation",
                 "Tracks are not explicitly beyond the platform edge.",
                 "Tracks remain beyond the platform edge.", rule_id="room_geometry",
                 repair="Restore the protected platform/track relationship.")
        if float(platform.get("minimum_character_edge_distance_m", 0)) < 1.2:
            fail("unsafe_platform_clearance", "spatial_plan.platform.minimum_character_edge_distance_m",
                 "Platform clearance is below 1.2 metres.", "Clearance is at least 1.2 metres.",
                 rule_id="circulation", repair="Move the actors farther from the edge.")

    if not results:
        results.append(_result(stage=stage, scene_id=scene_id, shot_id=None,
                               rule_id="continuity", status="pass", confidence=1.0,
                               evidence="All deterministic storyboard, spatial, privacy, and continuity checks passed.",
                               protected=["scene manifest", "location profile", "principal continuity", "privacy policy"]))
    blocking = sum(item["promotion_blocked"] for item in results)
    prompt_hashes = {shot["id"]: text_sha256(compile_prompt(scene, shot["id"]))
                     for shot in scene.get("shots", [])}
    catalog = _rule_catalog(scene)
    return {
        "schema_version": SCHEMA_VERSION,
        "audit_type": "storyboard_spatial",
        "audit_stage": stage,
        "scene_id": scene_id,
        "scene_sha256": canonical_sha256(scene),
        "gate": "pass" if blocking == 0 else "block",
        "promotion_status": "advance" if blocking == 0 else "blocked",
        "blocking_findings": blocking,
        "findings": findings,
        "results": results,
        "prompt_sha256s": prompt_hashes,
        "suggested_next_pipeline_stage": NEXT_STAGE[stage] if blocking == 0 else "storyboard",
        "required_draft_criteria": [
            {"id": key, "label": value.get("label", key), "description": value.get("expected", "")}
            for key, value in catalog.items() if key != "technical_validity"
        ],
    }


def _observation_map(observations: dict[str, Any]) -> dict[str, Any]:
    if isinstance(observations.get("rules"), list):
        return {str(item.get("rule_id")): item for item in observations["rules"] if isinstance(item, dict)}
    if isinstance(observations.get("rules"), dict):
        return observations["rules"]
    return observations.get("criteria", {}) if isinstance(observations.get("criteria"), dict) else {}


def audit_media_stage(scene: dict[str, Any], shot_id: str, video: str | Path, *, stage: str,
                      observations: dict[str, Any] | None = None,
                      contact_sheet_path: str | Path | None = None) -> dict[str, Any]:
    if stage not in {"cheap_draft", "final_candidate"}:
        raise ValueError("media audit stage must be cheap_draft or final_candidate")
    shot = next((item for item in scene.get("shots", []) if item.get("id") == shot_id), None)
    if shot is None:
        raise ValueError(f"unknown shot: {shot_id}")
    observations = observations or {}
    media = probe(video)
    video_streams = [item for item in media.get("streams", []) if item.get("codec_type") == "video"]
    audio_streams = [item for item in media.get("streams", []) if item.get("codec_type") == "audio"]
    duration = float(media.get("format", {}).get("duration", 0))
    duration_range = shot.get("source_duration_range")
    if isinstance(duration_range, list) and len(duration_range) == 2:
        minimum, maximum = map(float, duration_range)
    else:
        expected = float(shot.get("source_seconds", shot.get("seconds", 0)))
        minimum, maximum = expected - 0.3, expected + 0.3
    results: list[dict[str, Any]] = []
    technical_evidence = []
    if len(video_streams) != 1:
        technical_evidence.append(f"video streams={len(video_streams)}")
    if not minimum <= duration <= maximum:
        technical_evidence.append(f"duration={duration:.3f}, expected={minimum:.3f}–{maximum:.3f}")
    if stage == "final_candidate" and shot.get("dialogue") and not audio_streams:
        technical_evidence.append("dialogue candidate has no audio stream")
    results.append(_result(
        stage=stage, scene_id=scene.get("id"), shot_id=shot_id,
        rule_id="technical_validity", status="fail" if technical_evidence else "pass",
        confidence=1.0, evidence="; ".join(technical_evidence) or
        f"One video stream, {len(audio_streams)} audio stream(s), duration {duration:.3f}s.",
        repair="Retry identically only for a confirmed technical failure; otherwise repair the edit bounds.",
        protected=["billing status", "source request id", "synchronized source"]
    ))
    observation_values = _observation_map(observations)
    catalog = _rule_catalog(scene)
    for rule_id, data in catalog.items():
        if rule_id == "technical_validity":
            continue
        raw = observation_values.get(rule_id, "review")
        if isinstance(raw, str):
            status, confidence, evidence = raw, 1.0 if raw in {"pass", "fail"} else 0.5, ""
            severity, repair, protected = data.get("severity", "block"), "Review or repair this rule.", []
        elif isinstance(raw, dict):
            status = str(raw.get("status", "review"))
            confidence = float(raw.get("confidence", 0.5))
            evidence = str(raw.get("observed_evidence", raw.get("notes", "")))
            severity = str(raw.get("severity", data.get("severity", "block")))
            repair = str(raw.get("recommended_repair_action", "Review or repair this rule."))
            protected = list(raw.get("protected_constraints", []))
        else:
            status, confidence, evidence, severity, repair, protected = (
                "review", 0.5, "No observation supplied.", data.get("severity", "block"),
                "Complete human or model-assisted review before promotion.", [],
            )
        if status not in {"pass", "fail", "review"}:
            status, evidence = "review", f"Invalid observation status {status!r}."
        if status == "pass" and confidence < 0.7:
            status = "review"
            evidence = f"Low-confidence pass ({confidence:.2f}). {evidence}".strip()
        results.append(_result(
            stage=stage, scene_id=scene.get("id"), shot_id=shot_id, rule_id=rule_id,
            status=status, confidence=confidence, evidence=evidence or "Reviewer marked this rule pass.",
            expected=str(data.get("expected", "")), severity=severity, repair=repair,
            protected=protected,
        ))
    storyboard = audit_scene(scene)
    if storyboard["gate"] != "pass":
        results.append(_result(
            stage=stage, scene_id=scene.get("id"), shot_id=shot_id,
            rule_id="continuity", status="fail", confidence=1.0,
            evidence="The matching storyboard gate does not pass.",
            repair="Repair the storyboard before evaluating generated media.",
            protected=["storyboard hash", "prompt hash"], next_stage="storyboard",
        ))
    blocked = any(item["promotion_blocked"] for item in results)
    review = any(item["status"] == "review" for item in results)
    contact = None
    if contact_sheet_path is not None and Path(contact_sheet_path).is_file():
        path = Path(contact_sheet_path)
        contact = {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
    criteria = [{"id": item["rule_id"], "label": catalog.get(item["rule_id"], {}).get("label", item["rule_id"]),
                 "description": item["expected_condition"], "status": item["status"],
                 "notes": item["observed_evidence"]}
                for item in results if item["rule_id"] != "technical_validity"]
    promotion_status = "review" if review else ("blocked" if blocked else "advance")
    return {
        "schema_version": SCHEMA_VERSION,
        "audit_type": "draft_visual_spatial" if stage == "cheap_draft" else "final_candidate",
        "audit_stage": stage,
        "scene_id": scene.get("id"),
        "scene_sha256": canonical_sha256(scene),
        "shot_id": shot_id,
        "prompt_sha256": text_sha256(compile_prompt(scene, shot_id)),
        "media": {"path": str(video), "sha256": sha256_file(video), "bytes": Path(video).stat().st_size,
                  "duration_seconds": duration, "video_streams": len(video_streams), "audio_streams": len(audio_streams)},
        "contact_sheet": contact,
        "reviewer": observations.get("reviewer"),
        "results": results,
        "criteria": criteria,
        "technical_gate": "pass" if results[0]["status"] == "pass" else "block",
        "technical_findings": [] if results[0]["status"] == "pass" else [results[0]],
        "audio_plan": {"dialogue_present": shot.get("dialogue") is not None,
                       "audio_present_in_draft": bool(audio_streams),
                       "visible_lip_sync_required": stage == "final_candidate" and shot.get("dialogue") is not None,
                       "note": "Synchronized candidates retain their own audio and picture through every edit."},
        "promotion_allowed": not blocked,
        "promotion_status": promotion_status,
        "gate": "pass" if not blocked else ("review" if review else "block"),
        "suggested_next_pipeline_stage": NEXT_STAGE[stage] if not blocked else
        ("human_review" if review else stage),
    }


def audit_draft(scene: dict[str, Any], shot_id: str, video: str | Path,
                observations: dict[str, Any] | None = None,
                contact_sheet_path: str | Path | None = None) -> dict[str, Any]:
    return audit_media_stage(scene, shot_id, video, stage="cheap_draft",
                             observations=observations, contact_sheet_path=contact_sheet_path)


def audit_final_candidate(scene: dict[str, Any], shot_id: str, video: str | Path,
                          observations: dict[str, Any] | None = None,
                          contact_sheet_path: str | Path | None = None) -> dict[str, Any]:
    return audit_media_stage(scene, shot_id, video, stage="final_candidate",
                             observations=observations, contact_sheet_path=contact_sheet_path)


def audit_continuity(scene: dict[str, Any], observations: dict[str, Any], *,
                     stage: str = "cross_shot_continuity") -> dict[str, Any]:
    if stage not in {"cross_shot_continuity", "cross_scene_continuity", "final_sequence"}:
        raise ValueError("invalid continuity audit stage")
    required = ("master_coverage", "character_count_identity", "crowd_continuity",
                "blocking_and_framing", "gaze_and_eyeline", "wardrobe_construction",
                "prop_identity_ownership", "privacy", "lighting_continuity", "continuity")
    values = _observation_map(observations)
    results = []
    for rule_id in required:
        raw = values.get(rule_id, {})
        if isinstance(raw, str):
            status, confidence, evidence = raw, 1.0, ""
        else:
            status = str(raw.get("status", "review")) if isinstance(raw, dict) else "review"
            confidence = float(raw.get("confidence", 0.5)) if isinstance(raw, dict) else 0.5
            evidence = str(raw.get("observed_evidence", raw.get("notes", ""))) if isinstance(raw, dict) else ""
        if status == "pass" and confidence < 0.7:
            status = "review"
        results.append(_result(stage=stage, scene_id=scene.get("id"), shot_id=None,
                               rule_id=rule_id, status=status, confidence=confidence,
                               evidence=evidence or "No evidence supplied.",
                               repair="Identify the prior shot or reference frame and repair only the discontinuity.",
                               protected=["accepted prior interval", "principal identity", "scene geography"]))
    blocked = any(item["promotion_blocked"] for item in results)
    review = any(item["status"] == "review" for item in results)
    return {"schema_version": SCHEMA_VERSION, "audit_type": stage, "audit_stage": stage,
            "scene_id": scene.get("id"), "scene_sha256": canonical_sha256(scene),
            "results": results, "promotion_allowed": not blocked,
            "promotion_status": "review" if review else ("blocked" if blocked else "advance"),
            "gate": "pass" if not blocked else ("review" if review else "block"),
            "suggested_next_pipeline_stage": NEXT_STAGE[stage] if not blocked else
            ("human_review" if review else stage)}


def verify_storyboard_authorization(packet: dict[str, Any], shot_id: str, prompt: str) -> None:
    report = packet.get("spatial_audit", packet)
    if report.get("audit_type") != "storyboard_spatial" or report.get("gate") != "pass":
        raise ValueError("storyboard spatial audit did not pass")
    if report.get("prompt_sha256s", {}).get(shot_id) != text_sha256(prompt):
        raise ValueError("storyboard spatial audit does not match this shot prompt")


def verify_promotion_authorization(packet: dict[str, Any], prompt: str) -> None:
    if packet.get("audit_type") != "draft_visual_spatial" or not packet.get("promotion_allowed"):
        raise ValueError("draft visual-spatial audit does not authorize promotion")
    if packet.get("prompt_sha256") != text_sha256(prompt):
        raise ValueError("draft visual-spatial audit does not match this prompt")


def verify_bounded_repair_authorization(packet: dict[str, Any], prompt: str) -> None:
    """Authorize one repaired candidate without pretending the rejected draft passed."""
    if (packet.get("audit_type") != "bounded_repair_authorization" or
            packet.get("authorization_allowed") is not True):
        raise ValueError("bounded repair authorization is absent or denied")
    if packet.get("attempt_limit") != 1 or packet.get("attempts_used", 0) != 0:
        raise ValueError("bounded repair authorization is exhausted or unbounded")
    if packet.get("source_audit_gate") not in {"block", "review"}:
        raise ValueError("bounded repair must originate from a rejected or reviewed draft")
    if not packet.get("protected_constraints") or not packet.get("repair_actions"):
        raise ValueError("bounded repair must preserve constraints and declare repairs")
    if packet.get("repaired_prompt_sha256") != text_sha256(prompt):
        raise ValueError("bounded repair authorization does not match this repaired prompt")
