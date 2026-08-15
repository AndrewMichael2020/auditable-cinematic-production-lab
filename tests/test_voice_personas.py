import json
from pathlib import Path

import pytest

from video_gen.errors import PolicyError
from video_gen.config import ProjectConfig
from video_gen.voice_personas import (load_voice_plan, voice_audition_spec,
                                      dialogue_candidate_spec,
                                      voice_budget_report, voice_readiness_report)


REPO_ROOT = Path(__file__).resolve().parents[1]


def voice_plan_fixture(tmp_path: Path) -> Path:
    series = json.loads(
        (REPO_ROOT / "series/surrey-care/series.json").read_text(encoding="utf-8")
    )
    plan = json.loads(
        (REPO_ROOT / "sequences/clinic-full-cosmos-voice-plan.json").read_text(
            encoding="utf-8"
        )
    )
    for persona in series["canonical_personas"]:
        voice = persona.get("voice", {})
        if voice.get("contract_version") != "1.0":
            continue
        voice["active_voice_realization_id"] = None
        for realization in voice["voice_realizations"]:
            realization["status"] = "planned"
            realization["effective_from"] = None
            realization["audition"]["audio_sha256"] = None
            realization["audition"]["provider_request_id"] = None
    for master in plan["performance_masters"]:
        master["status"] = "planned"
        master["sha256"] = None
        master["audition_sha256"] = None
    for beat in plan["beats"]:
        if beat.get("voice_binding"):
            beat["voice_binding"]["audition_sha256"] = None
    anchor = tmp_path / "anchor.png"
    anchor.write_bytes(b"canonical-anchor")
    import hashlib

    plan["series_manifest"] = "series.json"
    plan["source_run"] = "source-run"
    plan["visual_anchor"] = {
        **plan["visual_anchor"],
        "path": "anchor.png",
        "sha256": hashlib.sha256(anchor.read_bytes()).hexdigest(),
    }
    (tmp_path / "source-run").mkdir()
    (tmp_path / "series.json").write_text(json.dumps(series), encoding="utf-8")
    destination = tmp_path / "plan.json"
    destination.write_text(json.dumps(plan), encoding="utf-8")
    return destination


def test_voice_plan_structurally_valid_but_blocks_motion_pending_human_review(tmp_path):
    plan = load_voice_plan(voice_plan_fixture(tmp_path))
    report = voice_readiness_report(plan)
    assert report["gate"] == "block"
    assert report["ready"] is False
    assert {
        item["character_id"] for item in report["findings"]
    } == {"nurse-maya", "patient-kenji"}
    assert {item["code"] for item in report["findings"]} == {
        "human_audition_pending"
    }
    budget = voice_budget_report(plan, ProjectConfig.load())
    assert budget["first_pass_reserved_usd"] == "4.25"
    assert budget["historical_voice_spend_usd"] == "0.0072"
    assert budget["maximum_planned_usd"] == "9.4972"
    assert budget["gate"] == "pass"


def test_dialogue_candidate_spec_uses_human_selected_voices_and_every_line(tmp_path):
    plan = load_voice_plan(voice_plan_fixture(tmp_path))
    spec = dialogue_candidate_spec(plan)
    assert spec["model_id"] == "eleven_v3"
    assert spec["output_format"] == "wav_24000"
    assert len(spec["inputs"]) == 6
    assert {item["voice_id"] for item in spec["inputs"]} == {
        "EXAVITQu4vr4xnSDxMaL",
        "pqHfZKP75CvOlQylNhV4",
    }
    assert [item["line"] for item in spec["turns"]] == [
        beat["line"] for beat in plan["beats"] if beat.get("speaker")
    ]
    assert all(item["text"].startswith("[") for item in spec["inputs"])


def test_voice_plan_rejects_a_dialogue_bound_to_the_wrong_persona(tmp_path):
    path = voice_plan_fixture(tmp_path)
    packet = json.loads(path.read_text(encoding="utf-8"))
    packet["beats"][1]["voice_binding"]["voice_persona_id"] = "vp-kenji-v01"
    path.write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(PolicyError, match="voice_persona_id is not canonical"):
        load_voice_plan(path)


def test_voice_plan_rejects_dot_separated_acronyms_in_spoken_content(tmp_path):
    path = voice_plan_fixture(tmp_path)
    packet = json.loads(path.read_text(encoding="utf-8"))
    packet["beats"][3]["line"] = "May I see your B.C. Service Card, please?"
    path.write_text(json.dumps(packet), encoding="utf-8")
    with pytest.raises(PolicyError, match="must not contain dot-separated acronyms"):
        load_voice_plan(path)


def test_revised_clinic_dialogue_uses_requested_language(tmp_path):
    plan = load_voice_plan(voice_plan_fixture(tmp_path))
    lines = {beat.get("dialogue_id"): beat.get("line") for beat in plan["beats"]}
    assert lines["dlg-maya-card-request"] == "May I see your BC Services Card, please?"
    assert lines["dlg-kenji-cost-question"].startswith("Oh no.")
    assert "Doctors of BC website" in lines["dlg-maya-final-answer"]
