import json
import shutil
import subprocess
from pathlib import Path

import pytest

from video_gen.errors import PolicyError
from video_gen.media import (assemble_stage2_timeline, generate_clinic_ambience,
                             mean_volume_dbfs, native_landscape_facts,
                             prepare_stage2_dialogue_clip,
                             prepare_stage2_square_dialogue_clip, probe)
from video_gen.stage2 import (HUMAN_GATES, audit_stage2_sequence,
                              compile_stage2_prompt, compile_stage2_take_prompt,
                              load_stage2_sequence)


ROOT = Path(__file__).resolve().parents[1]
SEQUENCE = ROOT / "sequences" / "clinic-reception-stage2.json"
ALLOWED_GENERATION_MODELS = {"Wan-AI/Wan2.2-T2V-A14B"}


def _video(path: Path, *, size: str = "1280x720", duration: float = 3.0,
           audio: bool = True) -> None:
    command = [
        "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
        f"color=c=0x145A68:s={size}:d={duration}:r=24",
    ]
    if audio:
        command.extend([
            "-f", "lavfi", "-i", f"sine=frequency=330:duration={duration}",
            "-shortest",
        ])
    command.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p"])
    if audio:
        command.extend(["-c:a", "aac"])
    command.append(str(path))
    subprocess.run(command, check=True)


def _interval(path: Path, index: int, *, role: str) -> dict:
    sequence = load_stage2_sequence(SEQUENCE)
    shot_id = f"shot0{index}"
    planned_shot = next(
        shot for scene in sequence["scenes"] for shot in scene["planned_shots"]
        if shot["shot_id"] == shot_id
    )
    canonical_versions = {
        persona["character_id"]: persona["persona_version"]
        for persona in sequence["_series"]["canonical_personas"]
    }
    persona_versions = {
        character_id: canonical_versions[character_id]
        for character_id in planned_shot["visible_characters"]
    }
    return {
        "id": f"int{index:02d}",
        "series_id": "ser-surrey-care",
        "season_id": "ssn01",
        "episode_id": "ep01",
        "sequence_id": "seq-clinic-care-card",
        "scene_id": "scn-clinic-reception",
        "setup_id": f"set0{min(index, 4)}",
        "take_id": f"take0{index}",
        "clip_id": f"clip0{index}",
        "shot_id": shot_id,
        "transition_after": "fade_out" if index == 4 else "cut",
        "transition_id": f"trn0{index}",
        "cut_after_id": None if index == 4 else f"cut0{index}",
        "generation_source_path": str(path),
        "generation_request_id": f"request-stage2-{index}",
        "generation_model_id": "Wan-AI/Wan2.2-T2V-A14B",
        "persona_versions": persona_versions,
        "source_role": role,
        "path": str(path),
        "start": 0.0,
        "end": 3.0,
        "rate": 1.0,
        "hold_after": 0.0,
        "include_audio": True,
        "sync_locked": True,
    }


def _approve_voice_realizations(sequence: dict) -> None:
    for persona in sequence["_series"]["canonical_personas"]:
        realization = persona["voice"].get("voice_realization")
        if realization is None:
            continue
        approval = realization["approval"]
        approval.update({
            "status": "approved",
            "audition_path": f"auditions/{persona['character_id']}.wav",
            "audition_sha256": "a" * 64,
            "reviewed_by": "test-reviewer",
            "reviewed_at": "2026-08-15T00:00:00Z",
        })


def test_loads_series_owned_personas_and_compiles_reference_anchored_prompt():
    sequence = load_stage2_sequence(SEQUENCE)
    prompt = compile_stage2_prompt(sequence, "shot05")

    assert sequence["hierarchy"]["series_id"] == "ser-surrey-care"
    assert {item["persona_version"] for item in sequence["episode"]["character_states"]} == {
        "pv01"
    }
    for anchor in sequence["reference_brief"]["high_weight_anchors"]:
        assert anchor in prompt
    planned_shot = next(
        item for scene in sequence["scenes"] for item in scene["planned_shots"]
        if item["shot_id"] == "shot05"
    )
    assert planned_shot["action"] in prompt
    assert "Native cinematic 16:9 landscape" in prompt
    paired_take = next(
        take for take in sequence["planned_source_takes"]
        if len(take["visible_characters"]) == 2
    )
    take_prompt = compile_stage2_take_prompt(sequence, paired_take["take_id"])
    assert "Generate both canonical principals together" in take_prompt
    single_take = next(
        take for take in sequence["planned_source_takes"]
        if len(take["visible_characters"]) == 1
    )
    single_take_prompt = compile_stage2_take_prompt(sequence, single_take["take_id"])
    assert "Generate the one canonical principal" in single_take_prompt
    assert "Generate both canonical principals" not in single_take_prompt
    for anchor in sequence["reference_brief"]["high_weight_anchors"]:
        assert anchor in take_prompt
    for requirement in sequence["reference_brief"]["functional_layout_checks"]:
        assert requirement in take_prompt
    question_prompt = compile_stage2_prompt(sequence, "shot02")
    assert sequence["_generation_prompt_policy"]["response_anticipation_clause"] in question_prompt


def test_stage2_manifest_records_unapproved_voice_realizations():
    sequence = load_stage2_sequence(SEQUENCE)
    statuses = {
        persona["character_id"]: persona["voice"]["voice_realization"]["approval"]["status"]
        for persona in sequence["_series"]["canonical_personas"]
        if "voice_realization" in persona["voice"]
    }

    assert statuses == {
        "nurse-amrit": "pending_human_audition",
        "patient-daniel": "not_auditioned",
    }


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg tools are required")
def test_stage2_preparation_rejects_portrait_source(tmp_path):
    portrait = tmp_path / "portrait.mp4"
    _video(portrait, size="720x1280", duration=2.0)

    with pytest.raises(PolicyError, match="native square-pixel 16:9"):
        prepare_stage2_dialogue_clip(
            portrait, tmp_path / "prepared.mp4", start=0.0, end=1.5, rate=1.0,
        )


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg tools are required")
def test_stage2_square_avatar_exception_delivers_safe_landscape(tmp_path):
    square = tmp_path / "square.mp4"
    origin = tmp_path / "origin.mp4"
    output = tmp_path / "dialogue.mp4"
    _video(square, size="960x960", duration=3.0)
    _video(origin, size="1280x720", duration=3.0)

    report = prepare_stage2_square_dialogue_clip(
        square, output, reference_origin=origin, start=0.0, end=2.5, rate=1.0,
        crop=(880, 495, 40, 220),
    )

    assert report["source_class"] == "approved_square_avatar_performance"
    assert report["source"]["portrait_origin"] is False
    assert report["padding"] is None
    assert report["av_transforms_identical"] is True
    assert native_landscape_facts(output)["native_landscape_16_9"] is True


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg tools are required")
def test_stage2_audit_accepts_complete_square_avatar_lineage(tmp_path):
    sequence = load_stage2_sequence(SEQUENCE)
    landscape = tmp_path / "landscape.mp4"
    square = tmp_path / "square.mp4"
    prepared = tmp_path / "prepared.mp4"
    _video(landscape)
    _video(square, size="960x960")
    prepare_stage2_square_dialogue_clip(
        square, prepared, reference_origin=landscape, start=0.0, end=2.5, rate=1.0,
        crop=(880, 495, 40, 220),
    )
    intervals = [
        _interval(landscape, 1, role="opening_master"),
        _interval(prepared, 2, role="dialogue_turn"),
        _interval(landscape, 3, role="essential_action"),
        _interval(landscape, 4, role="outro_reaction"),
    ]
    intervals[1].update({
        "generation_source_path": str(square),
        "generation_reference_origin_path": str(landscape),
        "performance_source_exception": "approved_square_avatar_performance",
        "generation_crop": {"width": 880, "height": 495, "x": 40, "y": 220},
    })
    ambience = tmp_path / "ambience.wav"
    generate_clinic_ambience(ambience, duration=12.0, fade_seconds=0.5)
    observations = {
        gate: {"status": "pass", "evidence": f"Reviewer passed {gate}."}
        for gate in HUMAN_GATES
    }

    report = audit_stage2_sequence(
        sequence, {"intervals": intervals, "ambience": str(ambience)},
        observations=observations,
        allowed_generation_models=ALLOWED_GENERATION_MODELS,
    )

    assert not any(
        item["gate_id"] == "native_origin" and item["status"] == "fail"
        for item in report["results"]
    )


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg tools are required")
def test_stage2_assembly_is_native_typed_audible_and_has_outer_fades(tmp_path):
    source = tmp_path / "landscape.mp4"
    _video(source)
    intervals = [
        _interval(source, 1, role="opening_master"),
        _interval(source, 2, role="dialogue_turn"),
        _interval(source, 3, role="essential_action"),
        _interval(source, 4, role="outro_reaction"),
    ]
    ambience = tmp_path / "clinic.wav"
    generate_clinic_ambience(ambience, duration=12.0, fade_seconds=0.5)
    output = tmp_path / "stage2.mp4"

    report = assemble_stage2_timeline(
        intervals, output, ambience=ambience, target_seconds=12.0, fade_seconds=0.5,
        ambience_volume=0.2,
    )

    assert report["native_landscape_only"] is True
    assert report["typed_lineage_required"] is True
    assert report["freeze_holds_allowed"] is False
    assert report["fade_in_seconds"] == 0.5
    assert report["ambience_volume"] == 0.2
    assert native_landscape_facts(output)["native_landscape_16_9"] is True
    assert mean_volume_dbfs(output, start=1.0, duration=2.0) > -50
    assert {item["codec_type"] for item in probe(output)["streams"]} == {"video", "audio"}


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg tools are required")
def test_stage2_audit_requires_human_evidence_and_passes_complete_candidate(tmp_path):
    sequence = load_stage2_sequence(SEQUENCE)
    _approve_voice_realizations(sequence)
    source = tmp_path / "landscape.mp4"
    _video(source)
    intervals = [
        _interval(source, 1, role="opening_master"),
        _interval(source, 2, role="dialogue_turn"),
        _interval(source, 3, role="essential_action"),
        _interval(source, 4, role="outro_reaction"),
    ]
    ambience = tmp_path / "clinic.wav"
    generate_clinic_ambience(ambience, duration=12.0, fade_seconds=0.5)
    timeline = {"intervals": intervals, "ambience": str(ambience)}
    observations = {
        gate: {"status": "pass", "evidence": f"Reviewer passed {gate}."}
        for gate in HUMAN_GATES
    }

    report = audit_stage2_sequence(
        sequence,
        timeline,
        observations=observations,
        allowed_generation_models=ALLOWED_GENERATION_MODELS,
    )

    assert report["gate"] == "pass"
    assert report["promotion_allowed"] is True
    assert report["blocking_findings"] == 0
    assert report["review_findings"] == 0

    missing_review = audit_stage2_sequence(
        sequence,
        timeline,
        allowed_generation_models=ALLOWED_GENERATION_MODELS,
    )
    assert missing_review["gate"] == "review"
    assert missing_review["review_findings"] == len(HUMAN_GATES)


def test_stage2_audit_blocks_legacy_portrait_and_untyped_timeline(tmp_path):
    sequence = load_stage2_sequence(SEQUENCE)
    timeline = {
        "intervals": [{
            "path": str(tmp_path / "missing-portrait.mp4"),
            "start": 0,
            "end": 1,
            "hold_after": 2,
            "source_role": "dialogue_turn",
        }],
    }

    report = audit_stage2_sequence(
        sequence,
        timeline,
        allowed_generation_models=ALLOWED_GENERATION_MODELS,
    )

    assert report["gate"] == "block"
    assert report["promotion_allowed"] is False
    failed = {item["gate_id"] for item in report["results"] if item["status"] == "fail"}
    assert {"typed_lineage", "source_exists", "intro", "outro", "ambience"} <= failed


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg tools are required")
def test_stage2_audit_rejects_unregistered_cinematic_source_model(tmp_path):
    sequence = load_stage2_sequence(SEQUENCE)
    source = tmp_path / "source.mp4"
    _video(source)
    intervals = [
        _interval(source, 1, role="opening_master"),
        _interval(source, 2, role="dialogue_turn"),
        _interval(source, 3, role="essential_action"),
        _interval(source, 4, role="outro_reaction"),
    ]
    intervals[2]["generation_model_id"] = "example/retired-low-quality-model"
    timeline = {"intervals": intervals, "ambience": str(source)}

    report = audit_stage2_sequence(
        sequence,
        timeline,
        allowed_generation_models=ALLOWED_GENERATION_MODELS,
    )

    assert report["gate"] == "block"
    assert any(
        item["gate_id"] == "cinematic_source_model" and item["status"] == "fail"
        for item in report["results"]
    )
