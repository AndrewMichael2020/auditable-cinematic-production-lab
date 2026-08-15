import json
import zipfile
from pathlib import Path

from video_gen.release_bundle import build_release_bundle, verify_release_bundle


ROOT = Path(__file__).resolve().parents[1]


def test_release_bundle_is_bounded_reproducible_and_verifiable(tmp_path: Path):
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    first_report = build_release_bundle(ROOT, first)
    second_report = build_release_bundle(ROOT, second)
    verified = verify_release_bundle(first)

    assert first_report["release_version"] == "0.2.0"
    assert first_report["bundle_sha256"] == second_report["bundle_sha256"]
    assert verified["credential_scan"] == "pass"
    assert verified["media_exclusion"] == "pass"
    assert first.stat().st_size < 8 * 1024 * 1024

    with zipfile.ZipFile(first) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read("MANIFEST.json"))
    assert names == sorted(names)
    assert not any(name.endswith((".mp4", ".wav", ".sqlite3")) for name in names)
    assert manifest["accepted_media_external"]["youtube"].startswith("https://")
