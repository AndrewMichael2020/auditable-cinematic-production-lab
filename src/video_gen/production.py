from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import PolicyError


SCENE_STATUSES = {"planned", "storyboard_passed", "drafting", "candidate", "final", "blocked"}
PROMOTION_STATUSES = {"pending", "advance", "repair", "review", "final", "blocked"}


def principal_characters(scene: dict[str, Any]) -> list[dict[str, Any]]:
    """Return speaking principals while preserving the legacy ``characters`` field."""
    value = scene.get("principal_characters", scene.get("characters", []))
    return value if isinstance(value, list) else []


def load_location_profile(path: str | Path) -> dict[str, Any]:
    profile = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"id", "location_type", "zones", "anchors", "circulation_paths"}
    missing = required - profile.keys()
    if missing:
        raise PolicyError(f"location profile missing: {', '.join(sorted(missing))}")
    zone_ids = [str(item.get("id", "")) for item in profile["zones"]]
    if not zone_ids or any(not item for item in zone_ids) or len(zone_ids) != len(set(zone_ids)):
        raise PolicyError("location profile zones must have unique non-empty ids")
    anchor_ids = [str(item.get("id", "")) for item in profile["anchors"]]
    if not anchor_ids or any(not item for item in anchor_ids) or len(anchor_ids) != len(set(anchor_ids)):
        raise PolicyError("location profile anchors must have unique non-empty ids")
    return profile


def location_profile_for_scene(scene: dict[str, Any]) -> dict[str, Any] | None:
    value = scene.get("location_profile")
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        return load_location_profile(value)
    return None


def _validate_scene(scene: dict[str, Any]) -> None:
    required = {"id", "duration_seconds", "location", "shots", "acceptance"}
    missing = required - scene.keys()
    if missing:
        raise PolicyError(f"scene missing: {', '.join(sorted(missing))}")
    characters = principal_characters(scene)
    if len(characters) != 2 or any(int(item.get("age", 0)) < 18 for item in characters):
        raise PolicyError("scene requires exactly two adult speaking principal characters")
    character_ids = [str(item.get("id", "")) for item in characters]
    if any(not item for item in character_ids) or len(character_ids) != len(set(character_ids)):
        raise PolicyError("principal character ids must be unique and non-empty")
    if not 4 <= len(scene["shots"]) <= 16:
        raise PolicyError("scene requires four to sixteen shots")
    ids = [shot.get("id") for shot in scene["shots"]]
    if len(set(ids)) != len(ids) or any(not item for item in ids):
        raise PolicyError("shot ids must be unique and non-empty")
    duration = sum(float(shot.get("seconds", 0)) for shot in scene["shots"])
    expected = float(scene["duration_seconds"])
    if abs(duration - expected) > 0.001 or not 12 <= duration <= 90:
        raise PolicyError("shot durations must equal a 12–90 second scene duration")
    for character in characters:
        for field in ("id", "description", "wardrobe"):
            if not str(character.get(field, "")).strip():
                raise PolicyError(f"character field is required: {field}")
    background = scene.get("background_population", {})
    if background:
        minimum = int(background.get("minimum_adults", -1))
        target = int(background.get("target_adults", -1))
        maximum = int(background.get("maximum_adults", -1))
        if not 0 <= minimum <= target <= maximum <= 100:
            raise PolicyError("background population must satisfy 0 <= minimum <= target <= maximum <= 100")
        occupancy = float(background.get("target_occupancy", -1))
        if not 0 <= occupancy <= 1:
            raise PolicyError("target occupancy must be between 0 and 1")


def load_scene(path: str | Path) -> dict[str, Any]:
    scene = json.loads(Path(path).read_text(encoding="utf-8"))
    _validate_scene(scene)
    if scene.get("location_profile"):
        location_profile_for_scene(scene)
    return scene


def load_production(path: str | Path) -> dict[str, Any]:
    """Load an ordered, independently resumable multi-scene production manifest."""
    source = Path(path)
    production = json.loads(source.read_text(encoding="utf-8"))
    required = {"id", "scenes", "continuity_state"}
    missing = required - production.keys()
    if missing:
        raise PolicyError(f"production missing: {', '.join(sorted(missing))}")
    scenes = production["scenes"]
    if not isinstance(scenes, list) or not scenes:
        raise PolicyError("production requires at least one ordered scene")
    orders = [int(item.get("order", -1)) for item in scenes]
    ids = [str(item.get("id", "")) for item in scenes]
    if orders != sorted(orders) or len(orders) != len(set(orders)):
        raise PolicyError("production scene order must be unique and ascending")
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        raise PolicyError("production scene ids must be unique and non-empty")
    known_ids: set[str] = set()
    for item in scenes:
        if item.get("status") not in SCENE_STATUSES:
            raise PolicyError(f"invalid scene status: {item.get('status')}")
        if item.get("promotion_status", "pending") not in PROMOTION_STATUSES:
            raise PolicyError(f"invalid promotion status: {item.get('promotion_status')}")
        manifest = Path(str(item.get("manifest", "")))
        if not manifest.is_file():
            manifest = source.parent / manifest
        loaded = load_scene(manifest)
        if loaded["id"] != item["id"]:
            raise PolicyError("production scene id must match its scene manifest")
        predecessor = item.get("inherits_from")
        if predecessor is not None and predecessor not in known_ids:
            raise PolicyError("scene inheritance must reference an earlier scene")
        known_ids.add(item["id"])
    return production


def production_scene(production: dict[str, Any], scene_id: str) -> dict[str, Any]:
    item = next((value for value in production["scenes"] if value["id"] == scene_id), None)
    if item is None:
        raise PolicyError(f"unknown production scene: {scene_id}")
    return load_scene(item["manifest"])


def compile_prompt(scene: dict[str, Any], shot_id: str) -> str:
    try:
        shot = next(value for value in scene["shots"] if value["id"] == shot_id)
    except StopIteration as exc:
        raise PolicyError(f"unknown shot: {shot_id}") from exc
    location = scene["location"]
    characters = principal_characters(scene)
    visible_ids = set(shot.get("visible_principals", [item["id"] for item in characters]))
    people_parts = []
    for character in characters:
        construction = ", ".join(
            f'{item["color"]} {item["item"]}: {item["construction"]}'
            for item in character.get("wardrobe_visual", [])
        )
        suffix = f"; wardrobe construction: {construction}" if construction else ""
        visibility = "visible" if character["id"] in visible_ids else "off camera"
        people_parts.append(
            f'{character["id"]} ({visibility}): {character["description"]}, '
            f'wearing {character["wardrobe"]}{suffix}'
        )
    blocking = shot.get("blocking", {})
    blocking_text = "; ".join(
        f'{character["id"]} {blocking.get(character["id"], {}).get("start", "unspecified").replace("_", " ")} '
        f'to {blocking.get(character["id"], {}).get("end", "unspecified").replace("_", " ")}'
        for character in characters
    )
    gaze_text = "; ".join(
        f'{character["id"]} looks {shot.get("gaze", {}).get(character["id"], {}).get("screen_direction", "unspecified").replace("_", " ")} '
        f'toward {shot.get("gaze", {}).get(character["id"], {}).get("target", "unspecified")}'
        for character in characters
    )
    background = scene.get("background_population", {})
    shot_background = shot.get("background_adults_visible", background.get("target_adults", 0))
    if isinstance(shot_background, list) and len(shot_background) == 2:
        background_text = f"approximately {shot_background[0]}–{shot_background[1]} background adults visible"
    else:
        background_text = f"approximately {shot_background} background adults visible"
    planned_prop_ids = set(shot.get("props_visible", [])) | set(shot.get("privacy_props_visible", []))
    has_prop_plan = "props_visible" in shot or "privacy_props_visible" in shot
    planned_props = [item for item in scene.get("props", [])
                     if not has_prop_plan or item.get("id") in planned_prop_ids]
    props = "; ".join(
        f'{item.get("id")}: {item.get("description", item.get("kind", "prop"))}; '
        f'privacy states {", ".join(item.get("allowed_visibility_states", []))}'
        for item in planned_props
    ) or "no featured prop"
    metaphors = "; ".join(scene.get("visual_policy", {}).get("environmental_metaphors", []))
    priority = str(shot.get("generation_priority", "")).strip()
    priority_text = f'ABSOLUTE COMPOSITION PRIORITY: {priority}. ' if priority else ""
    if shot.get("prompt_mode") == "environment_master":
        principal_summary = str(shot.get(
            "principal_summary", "Two speaking principals remain distant within the architecture."
        )).strip()
        return (
            f'{priority_text}Cinematic naturalistic drama, restrained prestige-series realism. '
            f'Location: {location["name"]}; {location["time"]}; {location["layout"]}; '
            f'lighting: {location["light"]}. Distant principals: {principal_summary}. '
            f'Background: {background_text}; '
            f'{shot.get("background_direction", background.get("behavior", "natural quiet activity"))}. '
            f'Continuity: {location["axis"]}. Shot: {shot["framing"]}. Action: {shot["action"]}. '
            f'Blocking: {blocking_text}. Eyelines: {gaze_text}. '
            'Room geometry, floor circulation, doors, chairs, counter, workstations, windows, people, '
            'scale, limbs and lighting direction remain physically plausible and stable. Exactly two '
            'speaking principal adults remain distant; all background adults are non-speaking and ignore them. '
            'Plain unreadable surfaces: no facility name, logo, signs, posters, captions, labels, letters, '
            'numbers, barcodes, patient information, readable monitor content, subtitles, or watermark. '
            'no actor looks into the camera; distant three-quarter profiles only. no visible lip-sync.'
        )
    if shot.get("prompt_mode") == "action_insert":
        principal_summary = str(shot.get(
            "principal_summary", "Speaking principals remain secondary to the planned physical action."
        )).strip()
        return (
            f'{priority_text}Cinematic naturalistic drama, restrained prestige-series realism. '
            f'Location: {location["name"]}; {location["time"]}; {location["layout"]}; '
            f'lighting: {location["light"]}. Principals: {principal_summary}. '
            f'Background: {background_text}; '
            f'{shot.get("background_direction", background.get("behavior", "natural quiet activity"))}. '
            f'Continuity: {location["axis"]}. Shot: {shot["framing"]}. Action: {shot["action"]}. '
            f'Blocking: {blocking_text}. Eyelines: {gaze_text}. Featured props: {props}. '
            'Preserve one stable prop, its colour, dimensions, ownership and exact hand-contact sequence. '
            'Hands have five distinct fingers and never fuse; the counter, body scale and circulation remain plausible. '
            'Exactly two speaking principal adults; background adults remain non-speaking and ignore the lens. '
            'Plain unreadable surfaces: no facility name, logo, signs, posters, captions, labels, letters, '
            'numbers, barcodes, patient information, readable monitor content, subtitles, badges, or watermark. '
            'no actor looks into the camera; use side angles and story-target eyelines. no visible lip-sync.'
        )
    return (
        f'{priority_text}Cinematic naturalistic drama, restrained prestige-series realism. Location: {location["name"]}; '
        f'{location["time"]}; {location["layout"]}; lighting: {location["light"]}. '
        f'Speaking principals: {"; ".join(people_parts)}. Background: {background_text}; '
        f'{shot.get("background_direction", background.get("behavior", "natural quiet activity"))}. '
        f'Continuity: {location["axis"]}. Shot: {shot["framing"]}. Action: {shot["action"]}. '
        f'Blocking: {blocking_text}. Eyelines: {gaze_text}. Props: {props}. '
        f'Environmental storytelling: {metaphors}. Room geometry, circulation, object support, anatomy, '
        'hands, scale, garment closures, physical contact, prop ownership, and lighting direction must remain plausible. '
        'Exactly two speaking principal adults; background adults are non-speaking and pay no unusual attention to them. '
        'Plain unreadable surfaces: no facility name, logo, signs, posters, captions, labels, letters, numbers, '
        'barcodes, patient information, readable monitor content, subtitles, or watermark. '
        'no actor looks into the camera; the lens remains an unnoticed observer. no visible lip-sync.'
    )
