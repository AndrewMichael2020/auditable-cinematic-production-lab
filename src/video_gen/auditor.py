from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .media import probe, sha256_file
from .production import compile_prompt


SCHEMA_VERSION = "1.0"
TEXT_BEARING_TERMS = (
    "advertisement", "caption", "label", "lettering", "menu", "poster",
    "sign", "signage", "subtitle", "timetable", "writing",
)
SAFE_CHARACTER_ZONES = {
    "left_safe_zone", "center_left_safe_zone", "center_safe_zone",
    "center_right_safe_zone", "right_safe_zone", "off_screen_left",
    "off_screen_right",
}
ZONE_POSITION = {
    "off_screen_left": -3,
    "left_safe_zone": -2,
    "center_left_safe_zone": -1,
    "center_safe_zone": 0,
    "center_right_safe_zone": 1,
    "right_safe_zone": 2,
    "off_screen_right": 3,
}
PLAUSIBLE_SUPPORTS = {
    "ground", "wall_mounted", "post_mounted", "ceiling_mounted",
    "structure_mounted",
}

DRAFT_CRITERIA = (
    ("platform_geometry", "Platform geometry",
     "The platform edge, tracks, safe standing area, and background could physically coexist."),
    ("safe_character_placement", "Safe character placement",
     "Characters remain on the platform safe side with clear edge and track relationships."),
    ("object_support", "Object support",
     "Benches, lamps, bags, and architecture have plausible support, mounting, and contact."),
    ("anatomy_contact", "Anatomy and contact",
     "Hands, feet, limbs, body contact, and object contact are anatomically plausible."),
    ("wardrobe_construction", "Wardrobe construction",
     "Buttons, closures, pockets, sleeves, scarves, straps, and accessories remain coherent."),
    ("character_scale", "Character scale",
     "People and objects retain plausible relative scale and perspective."),
    ("blocking_and_framing", "Blocking and framing",
     "Entrances, exits, screen direction, spacing, shot size, and camera movement match the plan."),
    ("gaze_and_eyeline", "Gaze and eyeline",
     "Every visible actor looks toward the planned scene partner or story object and never into the camera."),
    ("continuity", "Continuity",
     "Faces, wardrobe, layout, lighting, axis, and object anchors remain stable."),
    ("unwanted_text", "Unwanted text",
     "No malformed or unnecessary words, letters, numbers, captions, signs, or watermarks appear."),
    ("symbolic_environment", "Symbolic environment",
     "Meaning comes from light, weather, colour, distance, and architecture; icons are sparse and text-free."),
)


def canonical_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(data).hexdigest()


def text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _finding(code: str, message: str, path: str, severity: str = "block") -> dict[str, str]:
    return {"severity": severity, "code": code, "path": path, "message": message}


def audit_scene(scene: dict[str, Any]) -> dict[str, Any]:
    """Run deterministic storyboard, prompt, physical-world, and continuity checks."""
    findings: list[dict[str, str]] = []
    visual = scene.get("visual_policy")
    spatial = scene.get("spatial_plan")
    character_ids = {str(item.get("id")) for item in scene.get("characters", [])}

    if not isinstance(visual, dict):
        findings.append(_finding("missing_visual_policy", "Structured visual_policy is required.",
                                 "visual_policy"))
        visual = {}
    if not isinstance(spatial, dict):
        findings.append(_finding("missing_spatial_plan", "Structured spatial_plan is required.",
                                 "spatial_plan"))
        spatial = {}

    text_policy = visual.get("text_policy")
    if text_policy not in {"forbid", "essential_only"}:
        findings.append(_finding("invalid_text_policy", "text_policy must be forbid or essential_only.",
                                 "visual_policy.text_policy"))
    if text_policy == "forbid":
        location_text = " ".join(str(scene.get("location", {}).get(field, ""))
                                 for field in ("name", "layout", "light")).lower()
        for term in TEXT_BEARING_TERMS:
            if term in location_text:
                findings.append(_finding(
                    "text_environment_conflict",
                    f"No-text policy conflicts with location term: {term!r}.",
                    "location.layout",
                ))

    symbols = visual.get("public_space_symbols", {})
    if not isinstance(symbols, dict):
        findings.append(_finding("invalid_symbol_policy", "public_space_symbols must be an object.",
                                 "visual_policy.public_space_symbols"))
        symbols = {}
    max_icons = symbols.get("max_icons")
    allowed_icons = symbols.get("allowed_icons", [])
    if not isinstance(max_icons, int) or max_icons < 0 or max_icons > 2:
        findings.append(_finding("icon_density", "Public-space max_icons must be between 0 and 2.",
                                 "visual_policy.public_space_symbols.max_icons"))
    if not isinstance(allowed_icons, list) or (isinstance(max_icons, int) and len(allowed_icons) > max_icons):
        findings.append(_finding("icon_allowlist", "Allowed icons exceed the sparse icon limit.",
                                 "visual_policy.public_space_symbols.allowed_icons"))
    metaphors = visual.get("environmental_metaphors", [])
    if not isinstance(metaphors, list) or not 1 <= len(metaphors) <= 4:
        findings.append(_finding(
            "environmental_metaphor_density",
            "Provide one to four environmental metaphors using light, weather, colour, distance, or architecture.",
            "visual_policy.environmental_metaphors",
        ))
    if visual.get("camera_gaze_policy") != "never_look_at_camera":
        findings.append(_finding(
            "camera_gaze_policy",
            "visual_policy.camera_gaze_policy must forbid every actor from looking into the camera.",
            "visual_policy.camera_gaze_policy",
        ))

    platform = spatial.get("platform", {})
    safe_distance = platform.get("minimum_character_edge_distance_m") if isinstance(platform, dict) else None
    if not isinstance(safe_distance, (int, float)) or safe_distance < 1.2:
        findings.append(_finding(
            "unsafe_platform_clearance",
            "minimum_character_edge_distance_m must be at least 1.2 metres.",
            "spatial_plan.platform.minimum_character_edge_distance_m",
        ))
    if not isinstance(platform, dict) or platform.get("tracks_relation") != "beyond_platform_edge":
        findings.append(_finding(
            "ambiguous_track_geometry",
            "Tracks must be explicitly beyond the platform edge.",
            "spatial_plan.platform.tracks_relation",
        ))

    camera = spatial.get("camera", {})
    if not isinstance(camera, dict) or camera.get("side") != "platform_safe_side":
        findings.append(_finding("camera_axis_geometry", "Camera must remain on the platform safe side.",
                                 "spatial_plan.camera.side"))

    objects = spatial.get("objects", [])
    if not isinstance(objects, list) or not objects:
        findings.append(_finding("missing_object_anchors", "At least one anchored environmental object is required.",
                                 "spatial_plan.objects"))
        objects = []
    seen_objects: set[str] = set()
    for index, item in enumerate(objects):
        path = f"spatial_plan.objects[{index}]"
        if not isinstance(item, dict):
            findings.append(_finding("invalid_object_anchor", "Object anchor must be an object.", path))
            continue
        object_id = str(item.get("id", ""))
        if not object_id or object_id in seen_objects:
            findings.append(_finding("duplicate_object_anchor", "Object ids must be non-empty and unique.",
                                     f"{path}.id"))
        seen_objects.add(object_id)
        if item.get("support") not in PLAUSIBLE_SUPPORTS:
            findings.append(_finding("implausible_object_support", "Object needs an explicit plausible support.",
                                     f"{path}.support"))
        if text_policy == "forbid" and item.get("contains_text") is not False:
            findings.append(_finding("text_bearing_object", "No-text scenes require contains_text=false.",
                                     f"{path}.contains_text"))
        if item.get("kind") == "bench":
            distance = item.get("minimum_edge_distance_m")
            if not isinstance(distance, (int, float)) or distance < 2.0:
                findings.append(_finding("unsafe_bench_placement", "Bench must be at least 2 metres from the edge.",
                                         f"{path}.minimum_edge_distance_m"))
            if item.get("orientation") != "parallel_to_tracks":
                findings.append(_finding("bench_orientation", "Bench must be parallel to the tracks.",
                                         f"{path}.orientation"))
        if item.get("kind") == "lamp" and item.get("support") not in {"wall_mounted", "post_mounted"}:
            findings.append(_finding(
                "public_lamp_mounting",
                "Outdoor platform lamp must be wall- or post-mounted, not an indoor hanging fixture.",
                f"{path}.support",
            ))

    for index, character in enumerate(scene.get("characters", [])):
        checks = character.get("wardrobe_visual") if isinstance(character, dict) else None
        if not isinstance(checks, list) or not checks:
            findings.append(_finding(
                "missing_wardrobe_construction",
                "Each character requires structured wardrobe_visual construction anchors.",
                f"characters[{index}].wardrobe_visual",
            ))
            continue
        for item_index, item in enumerate(checks):
            if not isinstance(item, dict) or not all(str(item.get(field, "")).strip()
                                                     for field in ("item", "color", "construction")):
                findings.append(_finding(
                    "incomplete_wardrobe_construction",
                    "Wardrobe items require item, color, and construction.",
                    f"characters[{index}].wardrobe_visual[{item_index}]",
                ))

    master_shots = 0
    for index, shot in enumerate(scene.get("shots", [])):
        path = f"shots[{index}]"
        if shot.get("spatial_role") == "master":
            master_shots += 1
            if shot.get("camera", {}).get("framing") not in {"wide_master", "wide_full_body"}:
                findings.append(_finding(
                    "invalid_master_framing",
                    "The master shot must be a wide framing that establishes both actors and geography.",
                    f"{path}.camera.framing",
                ))
        blocking = shot.get("blocking") if isinstance(shot, dict) else None
        if not isinstance(blocking, dict):
            findings.append(_finding("missing_blocking", "Every shot requires structured character blocking.",
                                     f"{path}.blocking"))
            continue
        if set(blocking) - {"minimum_separation_m"} != character_ids:
            findings.append(_finding("blocking_characters", "Blocking must name every and only scene character.",
                                     f"{path}.blocking"))
        for character_id in character_ids:
            movement = blocking.get(character_id, {})
            if not isinstance(movement, dict):
                findings.append(_finding("invalid_blocking", "Character blocking must be an object.",
                                         f"{path}.blocking.{character_id}"))
                continue
            for endpoint in ("start", "end"):
                if movement.get(endpoint) not in SAFE_CHARACTER_ZONES:
                    findings.append(_finding(
                        "unsafe_character_zone",
                        f"{character_id} {endpoint} must use a declared safe/off-screen zone.",
                        f"{path}.blocking.{character_id}.{endpoint}",
                    ))
        separation = blocking.get("minimum_separation_m")
        if not isinstance(separation, (int, float)) or separation < 0.5:
            findings.append(_finding("character_separation", "Minimum separation must be at least 0.5 metres.",
                                     f"{path}.blocking.minimum_separation_m"))
        shot_camera = shot.get("camera", {})
        if not isinstance(shot_camera, dict) or not str(shot_camera.get("framing", "")).strip():
            findings.append(_finding("missing_camera_plan", "Each shot requires structured camera framing.",
                                     f"{path}.camera"))
        if "locked" in str(shot.get("framing", "")).lower() and shot_camera.get("movement") != "locked":
            findings.append(_finding("camera_movement_conflict", "Locked framing requires movement=locked.",
                                     f"{path}.camera.movement"))

        gaze = shot.get("gaze")
        if not isinstance(gaze, dict) or set(gaze) != character_ids:
            findings.append(_finding(
                "missing_gaze_plan",
                "Every shot must define gaze for every and only scene character.",
                f"{path}.gaze",
            ))
            continue
        for character_id in character_ids:
            instruction = gaze.get(character_id, {})
            gaze_path = f"{path}.gaze.{character_id}"
            if not isinstance(instruction, dict):
                findings.append(_finding("invalid_gaze_plan", "Gaze instruction must be an object.", gaze_path))
                continue
            target = instruction.get("target")
            direction = instruction.get("screen_direction")
            if target == "camera" or instruction.get("camera_look_forbidden") is not True:
                findings.append(_finding(
                    "camera_look",
                    "Actors must explicitly be forbidden from looking at the camera.",
                    gaze_path,
                ))
            if not str(target or "").strip():
                findings.append(_finding("missing_gaze_target", "Gaze target is required.", f"{gaze_path}.target"))
            if direction not in {"screen_left", "screen_right", "down"}:
                findings.append(_finding(
                    "invalid_eyeline_direction",
                    "Eyeline must be screen_left, screen_right, or down.",
                    f"{gaze_path}.screen_direction",
                ))
            if target in character_ids and target != character_id:
                actor_zone = blocking.get(character_id, {}).get("end")
                target_zone = blocking.get(target, {}).get("end")
                if actor_zone in ZONE_POSITION and target_zone in ZONE_POSITION:
                    expected = ("screen_right" if ZONE_POSITION[target_zone] > ZONE_POSITION[actor_zone]
                                else "screen_left")
                    if direction != expected:
                        findings.append(_finding(
                            "eyeline_axis_conflict",
                            f"{character_id} should look {expected} toward {target} from the planned blocking.",
                            f"{gaze_path}.screen_direction",
                        ))

    if master_shots < 1:
        findings.append(_finding(
            "missing_master_shot",
            "At least one wide master shot must establish both actors, the safe platform, and the scene axis.",
            "shots",
        ))

    prompt_hashes = {
        shot["id"]: text_sha256(compile_prompt(scene, shot["id"]))
        for shot in scene.get("shots", []) if isinstance(shot, dict) and shot.get("id")
    }
    blocking_count = sum(item["severity"] == "block" for item in findings)
    return {
        "schema_version": SCHEMA_VERSION,
        "audit_type": "storyboard_spatial",
        "scene_id": scene.get("id"),
        "scene_sha256": canonical_sha256(scene),
        "gate": "pass" if blocking_count == 0 else "block",
        "blocking_findings": blocking_count,
        "findings": findings,
        "prompt_sha256s": prompt_hashes,
        "required_draft_criteria": [
            {"id": item[0], "label": item[1], "description": item[2]}
            for item in DRAFT_CRITERIA
        ],
    }


def _observation_status(observations: dict[str, Any], criterion: str) -> tuple[str, str]:
    value = observations.get("criteria", {}).get(criterion, "pending")
    if isinstance(value, str):
        return value, ""
    if isinstance(value, dict):
        return str(value.get("status", "pending")), str(value.get("notes", ""))
    return "pending", ""


def audit_draft(scene: dict[str, Any], shot_id: str, video: str | Path,
                observations: dict[str, Any] | None = None,
                contact_sheet_path: str | Path | None = None) -> dict[str, Any]:
    """Combine technical media facts with explicit visual-spatial observations."""
    shot = next((item for item in scene.get("shots", []) if item.get("id") == shot_id), None)
    if shot is None:
        raise ValueError(f"unknown shot: {shot_id}")
    observations = observations or {}
    media = probe(video)
    video_streams = [item for item in media.get("streams", []) if item.get("codec_type") == "video"]
    audio_streams = [item for item in media.get("streams", []) if item.get("codec_type") == "audio"]
    duration = float(media.get("format", {}).get("duration", 0))
    expected_duration = float(shot.get("seconds", 0))
    technical_findings: list[dict[str, str]] = []
    if len(video_streams) != 1:
        technical_findings.append(_finding("video_stream_count", "Exactly one video stream is required.", "media"))
    if not expected_duration - 0.25 <= duration <= expected_duration + 0.25:
        technical_findings.append(_finding("duration_mismatch", "Clip duration is outside ±0.25 seconds.",
                                           "media.duration"))
    if video_streams and (int(video_streams[0].get("width", 0)) <= 0 or
                          int(video_streams[0].get("height", 0)) <= 0):
        technical_findings.append(_finding("invalid_dimensions", "Video dimensions must be positive.",
                                           "media.streams[0]"))

    criteria: list[dict[str, str]] = []
    allowed_statuses = {"pass", "fail", "uncertain", "pending"}
    for criterion_id, label, description in DRAFT_CRITERIA:
        status, notes = _observation_status(observations, criterion_id)
        if status not in allowed_statuses:
            status, notes = "fail", f"Invalid status in observations: {status!r}"
        criteria.append({"id": criterion_id, "label": label, "description": description,
                         "status": status, "notes": notes})

    scene_report = audit_scene(scene)
    semantics_pass = all(item["status"] == "pass" for item in criteria)
    technical_pass = not technical_findings
    promotion_allowed = scene_report["gate"] == "pass" and technical_pass and semantics_pass
    contact = None
    if contact_sheet_path is not None:
        path = Path(contact_sheet_path)
        if path.is_file():
            contact = {"path": str(path), "sha256": sha256_file(path), "bytes": path.stat().st_size}
    return {
        "schema_version": SCHEMA_VERSION,
        "audit_type": "draft_visual_spatial",
        "scene_id": scene.get("id"),
        "scene_sha256": scene_report["scene_sha256"],
        "shot_id": shot_id,
        "prompt_sha256": text_sha256(compile_prompt(scene, shot_id)),
        "media": {
            "path": str(video),
            "sha256": sha256_file(video),
            "bytes": Path(video).stat().st_size,
            "duration_seconds": duration,
            "video_streams": len(video_streams),
            "audio_streams": len(audio_streams),
        },
        "audio_plan": {
            "dialogue_present": shot.get("dialogue") is not None,
            "audio_present_in_draft": bool(audio_streams),
            "visible_lip_sync_required": False,
            "note": "Video drafts are silent; dialogue audio and any lip-sync are separate production stages.",
        },
        "contact_sheet": contact,
        "technical_gate": "pass" if technical_pass else "block",
        "technical_findings": technical_findings,
        "reviewer": observations.get("reviewer"),
        "criteria": criteria,
        "promotion_allowed": promotion_allowed,
        "gate": "pass" if promotion_allowed else "block",
    }


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
