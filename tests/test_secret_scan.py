from pathlib import Path

from video_gen.secret_scan import scan_files


def test_secret_scan_reports_path_and_label_without_secret_value(tmp_path: Path):
    secret = "ghp_" + "A" * 40
    source = tmp_path / "leak.txt"
    source.write_text(f"token={secret}\n", encoding="utf-8")

    findings = scan_files([source])

    assert findings == [(source, "GitHub token")]
    assert secret not in repr(findings)


def test_secret_scan_ignores_placeholders_and_binary_files(tmp_path: Path):
    placeholder = tmp_path / "example.env"
    placeholder.write_text("DEEPINFRA_TOKEN=${DEEPINFRA_TOKEN}\n", encoding="utf-8")
    binary = tmp_path / "clip.mp4"
    binary.write_bytes(b"\0" + ("ghp_" + "A" * 40).encode())

    assert scan_files([placeholder, binary]) == []
