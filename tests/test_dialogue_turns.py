import json
import wave
from pathlib import Path

import pytest

from video_gen.dialogue_turns import prepare_dialogue_turns
from video_gen.errors import PolicyError


def write_pcm_wav(path: Path, seconds: float = 3.0, sample_rate: int = 1000) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x01\x00" * round(seconds * sample_rate))


def packets(tmp_path: Path) -> tuple[Path, Path, Path]:
    audio = tmp_path / "candidate.wav"
    manifest = tmp_path / "candidate.json"
    plan = tmp_path / "plan.json"
    write_pcm_wav(audio)
    manifest.write_text(json.dumps({
        "candidate_id": "candidate-c01",
        "turns": [
            {"dialogue_id": "line-one", "speaker": "maya", "line": "One"},
            {"dialogue_id": "line-two", "speaker": "kenji", "line": "Two"},
        ],
        "voice_segments": [
            {"dialogue_input_index": 0, "start_time_seconds": 0.0, "end_time_seconds": 1.0},
            {"dialogue_input_index": 1, "start_time_seconds": 1.0, "end_time_seconds": 2.5},
        ],
    }), encoding="utf-8")
    plan.write_text(json.dumps({
        "beats": [
            {"dialogue_id": "line-one", "speaker": "maya", "seconds": 2},
            {"dialogue_id": "line-two", "speaker": "kenji", "seconds": 3},
        ]
    }), encoding="utf-8")
    return audio, manifest, plan


def test_splits_pcm_candidate_with_padding_without_stretching(tmp_path):
    audio, manifest, plan = packets(tmp_path)
    report = prepare_dialogue_turns(audio, manifest, plan, tmp_path / "turns", lead_in_seconds=0.25)
    assert report["preservation"] == {
        "speech_stretched": False,
        "speech_resampled": False,
        "padding_only": True,
        "boundary_source": "provider_turn_timestamps_with_final_audio_tail",
    }
    assert [item["target_seconds"] for item in report["turns"]] == [2.0, 3.0]
    assert report["turns"][0]["source_end_seconds"] == 1.0
    assert report["turns"][0]["source_end_extended_to_audio_end"] is False
    assert report["turns"][1]["provider_reported_end_seconds"] == 2.5
    assert report["turns"][1]["source_end_seconds"] == 3.0
    assert report["turns"][1]["source_end_extended_to_audio_end"] is True
    for expected, item in zip((2.0, 3.0), report["turns"], strict=True):
        with wave.open(item["output_path"], "rb") as prepared:
            assert prepared.getnframes() / prepared.getframerate() == pytest.approx(expected)


def test_uses_audited_word_gaps_instead_of_early_provider_boundaries(tmp_path):
    audio, manifest, plan = packets(tmp_path)
    asr = tmp_path / "asr.json"
    asr.write_text(json.dumps({
        "words": [
            {"word": " One", "start": 0.2, "end": 0.8},
            {"word": " Two", "start": 1.7, "end": 2.4},
        ]
    }), encoding="utf-8")

    report = prepare_dialogue_turns(
        audio, manifest, plan, tmp_path / "turns", lead_in_seconds=0.25,
        asr_audit=asr,
    )

    first, second = report["turns"]
    assert report["preservation"]["boundary_source"] == "audited_asr_word_gaps"
    assert first["source_start_seconds"] == 0.0
    assert first["source_end_seconds"] == pytest.approx(1.25)
    assert second["source_start_seconds"] == pytest.approx(1.25)
    assert second["source_end_seconds"] == 3.0
    assert first["asr_speech_end_seconds"] == 0.8
    assert second["asr_speech_start_seconds"] == 1.7


def test_rejects_turn_that_cannot_fit_storyboard_duration(tmp_path):
    audio, manifest, plan = packets(tmp_path)
    packet = json.loads(plan.read_text(encoding="utf-8"))
    packet["beats"][1]["seconds"] = 1
    plan.write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(PolicyError, match="exceeds storyboard duration"):
        prepare_dialogue_turns(audio, manifest, plan, tmp_path / "turns")
