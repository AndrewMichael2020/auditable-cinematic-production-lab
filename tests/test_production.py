import copy

import pytest

from video_gen.errors import PolicyError
from video_gen.production import compile_prompt, load_scene


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
