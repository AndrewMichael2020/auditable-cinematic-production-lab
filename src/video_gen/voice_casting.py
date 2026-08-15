from __future__ import annotations

import re
from typing import Any

from .errors import PolicyError


MATCH_PROFILE_FIELDS = (
    "gender",
    "age_priority",
    "accent_priority",
    "descriptors",
    "avoid_descriptors",
)


def validate_matching_profile(voice: dict[str, Any], *, context: str) -> None:
    """Validate the provider-neutral traits used to shortlist voice realizations."""
    profile = voice.get("matching_profile")
    if not isinstance(profile, dict):
        raise PolicyError(f"{context} requires matching_profile")
    for field in MATCH_PROFILE_FIELDS:
        value = profile.get(field)
        if field == "gender":
            if not isinstance(value, str) or not value.strip():
                raise PolicyError(f"{context} matching_profile requires gender")
            continue
        if not isinstance(value, list) or not value or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise PolicyError(f"{context} matching_profile requires non-empty {field}")
    if profile.get("protected_attributes_excluded") is not True:
        raise PolicyError(
            f"{context} matching_profile must exclude protected attributes"
        )


def _normal(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _ranked_score(value: str, priorities: list[str], weights: list[int]) -> int:
    normalized = _normal(value)
    for index, preference in enumerate(priorities):
        if normalized == _normal(preference):
            return weights[min(index, len(weights) - 1)]
    return 0


def rank_voice_catalog(
    persona: dict[str, Any], voices: list[dict[str, Any]], *, limit: int = 5
) -> list[dict[str, Any]]:
    """Rank a live provider catalog using only explicit vocal characteristics.

    Appearance, name, ethnicity, and cultural background are deliberately not
    read from the persona. The result is a shortlist, never an automatic cast.
    """
    if limit < 1:
        raise PolicyError("voice shortlist limit must be positive")
    voice_contract = persona.get("voice")
    if not isinstance(voice_contract, dict):
        raise PolicyError("persona requires a voice contract")
    context = f"persona {persona.get('character_id', '<unknown>')} voice"
    validate_matching_profile(voice_contract, context=context)
    profile = voice_contract["matching_profile"]
    target_gender = _normal(profile["gender"])
    age_priority = [str(item) for item in profile["age_priority"]]
    accent_priority = [str(item) for item in profile["accent_priority"]]
    desired = [_normal(item) for item in profile["descriptors"]]
    avoided = [_normal(item) for item in profile["avoid_descriptors"]]

    ranked: list[dict[str, Any]] = []
    for candidate in voices:
        if not isinstance(candidate, dict):
            continue
        voice_id = str(candidate.get("voice_id", "")).strip()
        name = str(candidate.get("name", "")).strip()
        labels = candidate.get("labels")
        if not voice_id or not name or not isinstance(labels, dict):
            continue
        gender = _normal(labels.get("gender"))
        if gender != target_gender:
            continue

        score = 100
        reasons = [f"gender:{gender}"]
        age = _normal(labels.get("age"))
        age_score = _ranked_score(age, age_priority, [30, 20, 10, 5])
        if age_score:
            score += age_score
            reasons.append(f"age:{age}")
        accent = _normal(labels.get("accent"))
        accent_score = _ranked_score(accent, accent_priority, [24, 14, 8, 4])
        if accent_score:
            score += accent_score
            reasons.append(f"accent:{accent}")

        searchable = _normal(" ".join(
            [str(candidate.get("description", ""))]
            + [str(value) for value in labels.values()]
        ))
        descriptor_matches = [item for item in desired if item in searchable]
        avoided_matches = [item for item in avoided if item in searchable]
        score += 3 * len(descriptor_matches)
        score -= 8 * len(avoided_matches)
        reasons.extend(f"trait:{item}" for item in descriptor_matches)
        reasons.extend(f"avoid:{item}" for item in avoided_matches)

        ranked.append({
            "voice_id": voice_id,
            "name": name,
            "score": score,
            "reasons": reasons,
            "labels": {
                key: str(labels[key])
                for key in ("gender", "age", "accent", "description", "use_case")
                if labels.get(key)
            },
            "description": str(candidate.get("description", "")),
            "preview_url": candidate.get("preview_url"),
            "selection_status": "requires_human_approval",
        })

    ranked.sort(key=lambda item: (-item["score"], item["name"].lower()))
    return ranked[:limit]
