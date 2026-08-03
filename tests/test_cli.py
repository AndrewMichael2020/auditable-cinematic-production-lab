from pathlib import Path

import pytest

from video_gen.cli import avatar_image_input
from video_gen.errors import VideoGenError


def test_avatar_image_input_allows_https_for_live_generation():
    assert avatar_image_input("https://example.test/actor.jpg", live=True) == (
        "https://example.test/actor.jpg"
    )


def test_avatar_image_input_rejects_local_file_before_live_reservation(tmp_path: Path):
    image = tmp_path / "actor.jpg"
    image.write_bytes(b"not-decoded-by-this-boundary")

    with pytest.raises(VideoGenError, match="public HTTPS"):
        avatar_image_input(image, live=True)


def test_avatar_image_input_keeps_data_url_for_dry_run(tmp_path: Path):
    image = tmp_path / "actor.png"
    image.write_bytes(b"dry-run-reference")

    assert avatar_image_input(image).startswith("data:image/png;base64,")
