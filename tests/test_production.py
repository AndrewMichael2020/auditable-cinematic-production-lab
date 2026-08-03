import copy

import pytest

from video_gen.errors import PolicyError
from video_gen.production import compile_prompt, load_production, load_scene


def test_golden_scene_is_complete_and_prompt_repeats_continuity():
    scene = load_scene("scenes/golden-scene.json")
    prompt = compile_prompt(scene, "s02")
    assert scene["duration_seconds"] == 20
    assert "mustard raincoat" in prompt
    assert "screen left" in prompt
    assert "no visible lip-sync" in prompt


def test_invalid_scene_is_rejected(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"id":"bad"}')
    with pytest.raises(PolicyError, match="missing"):
        load_scene(path)


def test_cliffhanger_scene_has_master_multiple_turns_and_gaze_control():
    scene = load_scene("scenes/platform-cliffhanger.json")
    assert scene["duration_seconds"] == 15
    assert len([shot for shot in scene["shots"] if shot.get("dialogue")]) == 4
    assert any(shot.get("spatial_role") == "master" for shot in scene["shots"])
    prompt = compile_prompt(scene, "c03")
    assert "no actor looks into the camera" in prompt
    assert "toward mara" in prompt


def test_clinic_scene_and_ordered_production_are_backward_compatible():
    scene = load_scene("scenes/clinic-reception-coverage.json")
    production = load_production("productions/robustness-tests.json")
    assert scene["duration_seconds"] == 56
    assert len(scene["shots"]) == 12
    assert scene["background_population"]["target_adults"] == 10
    assert [item["id"] for item in production["scenes"]] == [
        "last-train-platform-cliffhanger", "clinic-reception-coverage-check",
    ]
    prompt = compile_prompt(scene, "c02-foreshadow")
    assert "foreshadow_card" in prompt
    assert "patient_card" not in prompt
    assert "no actor looks into the camera" in prompt
    master_prompt = compile_prompt(scene, "c01-master")
    assert scene["shots"][0]["prompt_mode"] == "environment_master"
    assert "entire room floor" in master_prompt
    assert "five evenly spaced buttons" not in master_prompt
    assert scene["shots"][1]["prompt_mode"] == "action_insert"
    assert "one stable prop" in prompt
