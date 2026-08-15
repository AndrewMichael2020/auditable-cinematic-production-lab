from pathlib import Path

import pytest

from video_gen.cli import (avatar_image_input, image_video_audio_input,
                           image_video_input)
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


def test_i2v_local_assets_require_explicit_live_inline_opt_in(tmp_path: Path):
    image = tmp_path / "plate.png"
    image.write_bytes(b"image")
    audio = tmp_path / "line.wav"
    audio.write_bytes(b"audio")

    with pytest.raises(VideoGenError, match="inline-local-assets"):
        image_video_input(image, live=True)
    with pytest.raises(VideoGenError, match="inline-local-assets"):
        image_video_audio_input(audio, live=True)
    assert image_video_input(
        image, live=True, allow_live_inline=True
    ).startswith("data:image/png;base64,")
    assert image_video_audio_input(
        audio, live=True, allow_live_inline=True
    ).startswith("data:audio/x-wav;base64,")
