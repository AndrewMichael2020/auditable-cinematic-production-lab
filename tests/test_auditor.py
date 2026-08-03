import copy

import video_gen.auditor as auditor
from video_gen.auditor import DRAFT_CRITERIA, audit_draft, audit_scene
from video_gen.production import compile_prompt, load_scene


def test_golden_storyboard_passes_spatial_gate_and_avoids_text_objects():
    scene = load_scene("scenes/golden-scene.json")
    report = audit_scene(scene)
    assert report["gate"] == "pass"
    assert report["findings"] == []
    prompt = compile_prompt(scene, "s01")
    assert "timetable" not in prompt.lower()
    assert "wall-mounted amber lamp" in prompt
    assert "five evenly spaced buttons" in prompt
    assert "no actor looks into the camera" in prompt
    assert "mara looks screen right toward eli" in prompt


def test_storyboard_blocks_text_conflict_and_unsafe_bench():
    scene = load_scene("scenes/golden-scene.json")
    broken = copy.deepcopy(scene)
    broken["location"]["layout"] += ", timetable frame right"
    broken["spatial_plan"]["objects"][0]["minimum_edge_distance_m"] = 0.5
    report = audit_scene(broken)
    assert report["gate"] == "block"
    codes = {item["code"] for item in report["findings"]}
    assert "text_environment_conflict" in codes
    assert "unsafe_bench_placement" in codes


def test_storyboard_blocks_missing_master_and_camera_gaze():
    scene = load_scene("scenes/golden-scene.json")
    broken = copy.deepcopy(scene)
    broken["shots"][0]["spatial_role"] = "coverage"
    broken["shots"][1]["gaze"]["mara"] = {
        "target": "camera", "screen_direction": "screen_right", "camera_look_forbidden": False,
    }
    report = audit_scene(broken)
    codes = {item["code"] for item in report["findings"]}
    assert "missing_master_shot" in codes
    assert "camera_look" in codes


def test_draft_blocks_pending_review_and_passes_complete_review(tmp_path, monkeypatch):
    scene = load_scene("scenes/golden-scene.json")
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"video")
    monkeypatch.setattr(auditor, "probe", lambda path: {
        "format": {"duration": "5.0625"},
        "streams": [{"codec_type": "video", "width": 832, "height": 480}],
    })

    pending = audit_draft(scene, "s02", video)
    assert pending["promotion_allowed"] is False
    assert pending["audio_plan"]["dialogue_present"] is True
    assert pending["audio_plan"]["audio_present_in_draft"] is False

    observations = {
        "reviewer": "human:test",
        "criteria": {criterion[0]: "pass" for criterion in DRAFT_CRITERIA},
    }
    passed = audit_draft(scene, "s02", video, observations)
    assert passed["promotion_allowed"] is True
    assert passed["reviewer"] == "human:test"
