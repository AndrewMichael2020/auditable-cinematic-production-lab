import shutil
import subprocess

import pytest

from video_gen.media import assemble_lipsynced_dialogue, assemble_with_audio, probe


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg tools are required")
def test_assembles_eight_second_clip_with_video_and_audio(tmp_path):
    video = tmp_path / "video.mp4"
    audio = tmp_path / "speech.wav"
    output = tmp_path / "proof.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
        "color=c=navy:s=128x72:d=1:r=16", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(video),
    ], check=True)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
        "sine=frequency=440:duration=1", str(audio),
    ], check=True)

    manifest = assemble_with_audio(video, audio, output, target_seconds=8.0,
                                   audio_delay_seconds=0.5)
    media = probe(output)
    assert manifest["actual_seconds"] == pytest.approx(8.0, abs=0.1)
    assert manifest["visible_lip_sync"] is False
    assert {item["codec_type"] for item in media["streams"]} == {"video", "audio"}


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="FFmpeg tools are required")
def test_assembles_two_lipsynced_speakers_to_eight_seconds(tmp_path):
    clips = [tmp_path / "mara.mp4", tmp_path / "eli.mp4"]
    for index, clip in enumerate(clips):
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
            f"color=c=0x{index + 1}{index + 1}2233:s=128x72:d=1:r=16",
            "-f", "lavfi", "-i", f"sine=frequency={440 + index * 110}:duration=1",
            "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(clip),
        ], check=True)

    output = tmp_path / "dialogue.mp4"
    manifest = assemble_lipsynced_dialogue(clips, output, target_seconds=8.0)
    media = probe(output)
    assert manifest["actual_seconds"] == pytest.approx(8.0, abs=0.1)
    assert manifest["speaker_count"] == 2
    assert manifest["visible_lip_sync"] is True
    assert {item["codec_type"] for item in media["streams"]} == {"video", "audio"}
