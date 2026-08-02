from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import PolicyError


def load_scene(path: str | Path) -> dict[str, Any]:
    scene = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"id", "duration_seconds", "location", "characters", "shots", "acceptance"}
    missing = required - scene.keys()
    if missing:
        raise PolicyError(f"scene missing: {', '.join(sorted(missing))}")
    if len(scene["characters"]) != 2 or any(int(c.get("age", 0)) < 18 for c in scene["characters"]):
        raise PolicyError("scene requires exactly two adult characters")
    if len(scene["shots"]) != 4:
        raise PolicyError("scene requires exactly four shots")
    ids = [shot.get("id") for shot in scene["shots"]]
    if len(set(ids)) != len(ids):
        raise PolicyError("shot ids must be unique")
    duration = sum(int(shot.get("seconds", 0)) for shot in scene["shots"])
    if duration != int(scene["duration_seconds"]) or not 15 <= duration <= 30:
        raise PolicyError("shot durations must equal a 15–30 second scene duration")
    for character in scene["characters"]:
        for field in ("id", "description", "wardrobe"):
            if not str(character.get(field, "")).strip():
                raise PolicyError(f"character field is required: {field}")
    return scene


def compile_prompt(scene: dict[str, Any], shot_id: str) -> str:
    try:
        shot = next(s for s in scene["shots"] if s["id"] == shot_id)
    except StopIteration as exc:
        raise PolicyError(f"unknown shot: {shot_id}") from exc
    location = scene["location"]
    people_parts = []
    for character in scene["characters"]:
        construction = ", ".join(
            f'{item["color"]} {item["item"]}: {item["construction"]}'
            for item in character.get("wardrobe_visual", [])
        )
        suffix = f"; wardrobe construction: {construction}" if construction else ""
        people_parts.append(f'{character["description"]}, wearing {character["wardrobe"]}{suffix}')
    people = "; ".join(people_parts)
    blocking = shot.get("blocking", {})
    blocking_text = "; ".join(
        f'{character["id"]} {blocking.get(character["id"], {}).get("start", "unspecified").replace("_", " ")} '
        f'to {blocking.get(character["id"], {}).get("end", "unspecified").replace("_", " ")}'
        for character in scene["characters"]
    )
    metaphors = "; ".join(scene.get("visual_policy", {}).get("environmental_metaphors", []))
    return (f'Cinematic naturalistic drama. Location: {location["name"]}; {location["time"]}; '
            f'{location["layout"]}; lighting: {location["light"]}. Characters: {people}. '
            f'Continuity: {location["axis"]}. Shot: {shot["framing"]}. Action: {shot["action"]}. '
            f'Blocking: {blocking_text}. Environmental storytelling: {metaphors}. '
            'The platform geometry, object supports, anatomy, scale, garment closures, and physical contact must remain plausible. '
            'Exactly two adults, stable wardrobe and setting, plain surfaces, no signs, no labels, no letters, no numbers, '
            'no subtitles, no watermark, no visible lip-sync.')
