from copy import deepcopy

from video_gen.voice_casting import rank_voice_catalog


def maya_persona():
    return {
        "character_id": "nurse-maya",
        "cultural_background": "must never affect matching",
        "appearance": "must never affect matching",
        "voice": {
            "matching_profile": {
                "gender": "female",
                "age_priority": ["middle_aged", "young"],
                "accent_priority": ["canadian", "american"],
                "descriptors": ["warm", "reassuring", "professional"],
                "avoid_descriptors": ["playful", "promotional"],
                "protected_attributes_excluded": True,
            }
        },
    }


def catalog():
    return [
        {
            "voice_id": "sarah",
            "name": "Sarah",
            "labels": {"gender": "female", "age": "young", "accent": "american"},
            "description": "Warm, reassuring, mature professional",
            "preview_url": "https://example/sarah.mp3",
        },
        {
            "voice_id": "matilda",
            "name": "Matilda",
            "labels": {"gender": "female", "age": "middle_aged", "accent": "american"},
            "description": "Professional alto",
            "preview_url": "https://example/matilda.mp3",
        },
        {
            "voice_id": "wrong-gender",
            "name": "Wrong",
            "labels": {"gender": "male", "age": "middle_aged", "accent": "canadian"},
            "description": "Warm reassuring professional",
        },
    ]


def test_dynamic_match_uses_vocal_profile_and_requires_human_approval():
    results = rank_voice_catalog(maya_persona(), catalog())
    assert [item["name"] for item in results] == ["Matilda", "Sarah"]
    assert all(item["selection_status"] == "requires_human_approval" for item in results)


def test_dynamic_match_is_invariant_to_protected_persona_attributes():
    original = maya_persona()
    changed = deepcopy(original)
    changed["cultural_background"] = "completely different background"
    changed["appearance"] = "completely different appearance"
    assert rank_voice_catalog(original, catalog()) == rank_voice_catalog(changed, catalog())
