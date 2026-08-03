from video_gen.retention import audit_run_artifacts, prune_recomputable_artifacts


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
