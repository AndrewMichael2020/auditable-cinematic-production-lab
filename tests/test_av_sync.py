import json

import pytest

from video_gen.av_sync import audit_av_sync
from video_gen.cli import main
from video_gen.errors import PolicyError


def evidence(**overrides):
    packet = {
        "evidence_kind": "artifact_measurement",
        "artifact_id": "candidate-01",
        "target_max_absolute_offset_ms": 80,
        "measurement_cadence_ms": 20,
        "events": [
            {
                "event_id": "line-01",
                "audio_onset_ms": 1000,
                "visual_onset_ms": 1030,
                "confidence": 0.96,
            },
            {
                "event_id": "line-02",
                "audio_onset_ms": 2200,
                "visual_onset_ms": 2140,
                "confidence": 0.91,
            },
        ],
        "human_review": {
            "decision": "pass",
            "normal_speed": True,
            "sound_enabled": True,
            "reviewer": "portfolio-reviewer",
        },
    }
    packet.update(overrides)
    return packet


def test_artifact_requires_machine_and_normal_speed_human_pass():
    report = audit_av_sync(evidence())
    assert report["objective_gate"] == "pass"
    assert report["acceptance_gate"] == "pass"
    assert report["maximum_absolute_offset_ms"] == 60


def test_coarse_measurement_cannot_validate_eighty_millisecond_target():
    report = audit_av_sync(evidence(measurement_cadence_ms=50))
    assert report["cadence_capable"] is False
    assert report["objective_gate"] == "fail"
    assert report["acceptance_gate"] == "fail"


def test_pending_human_review_blocks_artifact_acceptance():
    report = audit_av_sync(evidence(human_review={"decision": "pending"}))
    assert report["objective_gate"] == "pass"
    assert report["acceptance_gate"] == "review"


def test_calibration_fixture_never_claims_artifact_acceptance():
    report = audit_av_sync(evidence(evidence_kind="calibration_fixture"))
    assert report["objective_gate"] == "pass"
    assert report["acceptance_gate"] == "not_applicable"


def test_invalid_confidence_fails_closed():
    packet = evidence()
    packet["events"][0]["confidence"] = 1.2
    with pytest.raises(PolicyError, match="between 0 and 1"):
        audit_av_sync(packet)


def test_cli_returns_review_for_unreviewed_artifact(tmp_path):
    packet = evidence(human_review={"decision": "pending"})
    source = tmp_path / "evidence.json"
    source.write_text(json.dumps(packet), encoding="utf-8")
    output = tmp_path / "report.json"

    assert main(["audit-av-sync", str(source), "--output", str(output)]) == 2
    assert json.loads(output.read_text())["acceptance_gate"] == "review"
