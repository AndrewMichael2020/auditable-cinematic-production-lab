import hashlib
import json

import pytest

from video_gen.errors import PolicyError
from video_gen.retention import (audit_run_artifacts, prune_recomputable_artifacts,
                                 prune_rejected_media)


def test_retention_keeps_masters_and_marks_only_derivatives(tmp_path):
    run = tmp_path / "run"
    frames = run / "frames"
    frames.mkdir(parents=True)
    (run / "accepted-scene.mp4").write_bytes(b"master")
    (run / "ledger.sqlite3").write_bytes(b"ledger")
    (run / "final-contact-sheet.png").write_bytes(b"sheet")
    (run / "mara-turn1-contact.png").write_bytes(b"turn sheet")
    (run / "eli-all-frames.png").write_bytes(b"all frames")
    (frames / "frame-01.png").write_bytes(b"frame")
    (run / "crop-preview.png").write_bytes(b"preview")

    report = audit_run_artifacts(run)
    categories = {item["relative_path"]: item["category"] for item in report["files"]}
    assert categories["accepted-scene.mp4"] == "retain"
    assert categories["ledger.sqlite3"] == "retain"
    assert categories["final-contact-sheet.png"] == "retain"
    assert categories["mara-turn1-contact.png"] == "recomputable"
    assert categories["eli-all-frames.png"] == "recomputable"
    assert categories["frames/frame-01.png"] == "recomputable"
    assert categories["crop-preview.png"] == "recomputable"


def test_prune_is_dry_run_by_default_and_apply_is_bounded(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    keep = run / "final.mp4"
    preview = run / "shot-preview.png"
    keep.write_bytes(b"keep")
    preview.write_bytes(b"remove")
    dry = prune_recomputable_artifacts(run)
    assert dry["mode"] == "dry_run"
    assert preview.exists()
    applied = prune_recomputable_artifacts(run, apply=True)
    assert applied["mode"] == "applied"
    assert keep.exists()
    assert not preview.exists()


def test_rejected_large_media_prune_keeps_review_evidence_and_lessons(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    rejected = run / "failed-take.mp4"
    rejected.write_bytes(b"large failed media")
    review = run / "failed-take-review.json"
    review.write_text('{"decision":"rejected"}')
    lessons = run / "LESSONS.md"
    lessons.write_text("Keep this production lesson.")
    decisions = run / "rejected-media.json"
    decisions.write_text(json.dumps({
        "schema_version": "1.0",
        "protected_paths": [],
        "decisions": [{
            "relative_path": "failed-take.mp4",
            "outcome": "rejected",
            "reason": "voice continuity failed human review",
            "sha256": hashlib.sha256(rejected.read_bytes()).hexdigest(),
            "retained_evidence": ["failed-take-review.json", "LESSONS.md"],
        }],
    }))

    dry = prune_rejected_media(run, decisions, minimum_bytes=1)
    assert dry["candidate_count"] == 1
    assert rejected.exists()
    applied = prune_rejected_media(run, decisions, minimum_bytes=1, apply=True)
    assert len(applied["removed"]) == 1
    assert not rejected.exists()
    assert review.exists()
    assert lessons.exists()
    assert decisions.exists()


def test_rejected_media_prune_refuses_anchor_even_if_listed(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    anchor = run / "clinic-anchor.mp4"
    anchor.write_bytes(b"anchor")
    evidence = run / "review.json"
    evidence.write_text("{}")
    decisions = run / "decisions.json"
    decisions.write_text(json.dumps({
        "schema_version": "1.0",
        "protected_paths": [],
        "decisions": [{
            "relative_path": "clinic-anchor.mp4",
            "outcome": "rejected",
            "reason": "mistaken decision",
            "sha256": hashlib.sha256(anchor.read_bytes()).hexdigest(),
            "retained_evidence": ["review.json"],
        }],
    }))

    with pytest.raises(PolicyError, match="protected media"):
        prune_rejected_media(run, decisions, minimum_bytes=1, apply=True)
    assert anchor.exists()
