from pathlib import Path

from video_gen.artifact_policy import evaluate_artifacts


def policy(threshold=10):
    return {
        "threshold_bytes": threshold,
        "legacy_large_files": {"runs/accepted.mp4": 12},
    }


def test_existing_readme_evidence_is_grandfathered(tmp_path: Path):
    artifact = tmp_path / "runs" / "accepted.mp4"
    artifact.parent.mkdir()
    artifact.write_bytes(b"x" * 12)

    report = evaluate_artifacts(tmp_path, [artifact], policy())
    assert report["gate"] == "pass"
    assert report["grandfathered_large_file_count"] == 1


def test_new_large_file_is_blocked(tmp_path: Path):
    artifact = tmp_path / "runs" / "new.bin"
    artifact.parent.mkdir()
    artifact.write_bytes(b"x" * 11)

    report = evaluate_artifacts(tmp_path, [artifact], policy())
    assert report["gate"] == "fail"
    assert report["violations"][0]["reason"].startswith("new tracked file")


def test_changed_run_media_is_blocked_even_when_small(tmp_path: Path):
    artifact = tmp_path / "runs" / "new.mp4"
    artifact.parent.mkdir()
    artifact.write_bytes(b"tiny")

    report = evaluate_artifacts(
        tmp_path, [artifact], policy(), changed={"runs/new.mp4"}
    )
    assert report["gate"] == "fail"
    assert "release asset" in report["violations"][0]["reason"]
