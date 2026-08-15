from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

from .errors import PolicyError


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: str | Path) -> dict:
    if not shutil.which("ffprobe"):
        raise PolicyError("ffprobe is required for media validation")
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                             "-of", "json", str(path)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def video_stream(path_or_packet: str | Path | dict) -> dict:
    packet = probe(path_or_packet) if not isinstance(path_or_packet, dict) else path_or_packet
    stream = next((item for item in packet.get("streams", [])
                   if item.get("codec_type") == "video"), None)
    if stream is None:
        raise PolicyError("media requires one video stream")
    return stream


def native_landscape_facts(path_or_packet: str | Path | dict) -> dict:
    """Return Stage 2 aspect facts without trusting a landscape output wrapper."""
    stream = video_stream(path_or_packet)
    width = int(stream.get("width", 0))
    height = int(stream.get("height", 0))
    sar = str(stream.get("sample_aspect_ratio", "1:1"))
    ratio = width / height if height else 0.0
    square_pixels = sar in {"1:1", "0:1", "N/A", "None", ""}
    approved_resolution = (width, height) in {(1280, 720), (1920, 1080)}
    is_landscape_16_9 = approved_resolution and abs(ratio - (16 / 9)) <= 0.01
    return {
        "width": width,
        "height": height,
        "sample_aspect_ratio": sar,
        "display_ratio": ratio,
        "square_pixels": square_pixels,
        "approved_stage2_resolution": approved_resolution,
        "native_landscape_16_9": square_pixels and is_landscape_16_9,
    }


def mean_volume_dbfs(path: str | Path, *, start: float, duration: float) -> float:
    """Measure mean audio level for an exact interval using FFmpeg volumedetect."""
    if not shutil.which("ffmpeg"):
        raise PolicyError("ffmpeg is required for audio measurement")
    if start < 0 or duration <= 0:
        raise PolicyError("audio measurement interval is invalid")
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-nostats", "-v", "info", "-ss", f"{start:.6f}",
        "-t", f"{duration:.6f}", "-i", str(path), "-vn", "-af", "volumedetect",
        "-f", "null", "-",
    ], check=True, capture_output=True, text=True)
    match = re.search(r"mean_volume:\s*(-?inf|[-+0-9.]+)\s*dB", result.stderr)
    if not match:
        raise PolicyError("could not measure audio mean volume")
    return float("-inf") if match.group(1) == "-inf" else float(match.group(1))


def contact_sheet(video: str | Path, output: str | Path) -> None:
    if not shutil.which("ffmpeg"):
        raise PolicyError("ffmpeg is required for contact sheets")
    duration = float(probe(video).get("format", {}).get("duration", 0))
    # fps=1 emits frames at whole-second timestamps beginning at zero. Using
    # ceil(duration / 5) creates a completely empty second row for common
    # 5.06-second provider clips, which obscures the actual review frames.
    sampled_frames = max(1, math.floor(max(duration, 1)))
    rows = max(1, math.ceil(sampled_frames / 5))
    subprocess.run(["ffmpeg", "-y", "-i", str(video), "-vf",
                    f"fps=1,scale=320:-1,tile=5x{rows}", "-frames:v", "1", str(output)],
                   check=True, capture_output=True)


def assemble_with_audio(video: str | Path, audio: str | Path, output: str | Path, *,
                        target_seconds: float = 8.0, audio_delay_seconds: float = 0.8) -> dict:
    """Build a bounded proof clip by holding the final frame and timing one dialogue track."""
    if not shutil.which("ffmpeg"):
        raise PolicyError("ffmpeg is required for assembly")
    if not 6.0 <= target_seconds <= 10.0:
        raise PolicyError("proof assembly must be between 6 and 10 seconds")
    if not 0 <= audio_delay_seconds < target_seconds:
        raise PolicyError("audio delay must fall inside the proof duration")
    video_probe = probe(video)
    audio_probe = probe(audio)
    video_duration = float(video_probe.get("format", {}).get("duration", 0))
    if video_duration <= 0 or video_duration > target_seconds:
        raise PolicyError("source video duration must be positive and no longer than the proof")
    if not any(item.get("codec_type") == "audio" for item in audio_probe.get("streams", [])):
        raise PolicyError("speech source has no audio stream")

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    hold_seconds = target_seconds - video_duration
    delay_ms = round(audio_delay_seconds * 1000)
    filter_graph = (
        f"[0:v]tpad=stop_mode=clone:stop_duration={hold_seconds:.6f},"
        f"trim=duration={target_seconds:.6f},setpts=PTS-STARTPTS[v];"
        f"[1:a]adelay={delay_ms}:all=1,apad=pad_dur={target_seconds:.6f},"
        f"atrim=duration={target_seconds:.6f}[a]"
    )
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(audio),
        "-filter_complex", filter_graph, "-map", "[v]", "-map", "[a]",
        "-t", f"{target_seconds:.6f}", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-ar", "48000", "-movflags", "+faststart", str(destination),
    ], check=True, capture_output=True)

    assembled = probe(destination)
    streams = assembled.get("streams", [])
    assembled_duration = float(assembled.get("format", {}).get("duration", 0))
    if sum(item.get("codec_type") == "video" for item in streams) != 1:
        raise PolicyError("assembled proof must contain one video stream")
    if sum(item.get("codec_type") == "audio" for item in streams) != 1:
        raise PolicyError("assembled proof must contain one audio stream")
    if abs(assembled_duration - target_seconds) > 0.1:
        raise PolicyError("assembled proof duration is outside tolerance")
    return {
        "schema_version": "1.0",
        "target_seconds": target_seconds,
        "actual_seconds": assembled_duration,
        "audio_delay_seconds": audio_delay_seconds,
        "held_final_frame_seconds": hold_seconds,
        "visible_lip_sync": False,
        "lip_sync_strategy": "wide-shot dialogue placement; no claimed mouth synchronization",
        "video": {"path": str(video), "sha256": sha256_file(video)},
        "speech": {"path": str(audio), "sha256": sha256_file(audio)},
        "output": {"path": str(destination), "sha256": sha256_file(destination),
                   "bytes": destination.stat().st_size},
    }


def assemble_lipsynced_dialogue(clips: list[str | Path], output: str | Path, *,
                                target_seconds: float = 8.0) -> dict:
    """Concatenate two already lip-synced speaker clips and hold the final frame if needed."""
    if not shutil.which("ffmpeg"):
        raise PolicyError("ffmpeg is required for assembly")
    if len(clips) != 2:
        raise PolicyError("dialogue proof requires exactly two speaker clips")
    if not 6.0 <= target_seconds <= 10.0:
        raise PolicyError("dialogue proof must be between 6 and 10 seconds")
    durations = []
    for clip in clips:
        packet = probe(clip)
        stream_types = {item.get("codec_type") for item in packet.get("streams", [])}
        if not {"video", "audio"}.issubset(stream_types):
            raise PolicyError("each lip-sync clip requires video and audio streams")
        durations.append(float(packet.get("format", {}).get("duration", 0)))
    source_seconds = sum(durations)
    if source_seconds <= 0 or source_seconds > target_seconds:
        raise PolicyError("speaker clips do not fit the target duration")

    hold_seconds = target_seconds - source_seconds
    filters = []
    for index in range(2):
        filters.append(
            f"[{index}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
            f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,fps=16,"
            f"format=yuv420p,setpts=PTS-STARTPTS[v{index}]"
        )
        filters.append(
            f"[{index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"asetpts=PTS-STARTPTS[a{index}]"
        )
    filters.append("[v0][a0][v1][a1]concat=n=2:v=1:a=1[cv][ca]")
    filters.append(
        f"[cv]tpad=stop_mode=clone:stop_duration={hold_seconds:.6f},"
        f"trim=duration={target_seconds:.6f}[v]"
    )
    filters.append(
        f"[ca]apad=pad_dur={target_seconds:.6f},atrim=duration={target_seconds:.6f},"
        "loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    )
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(clips[0]), "-i", str(clips[1]),
        "-filter_complex", ";".join(filters), "-map", "[v]", "-map", "[a]",
        "-t", f"{target_seconds:.6f}", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-ar", "48000", "-movflags", "+faststart", str(destination),
    ], check=True, capture_output=True)
    assembled = probe(destination)
    actual = float(assembled.get("format", {}).get("duration", 0))
    if abs(actual - target_seconds) > 0.1:
        raise PolicyError("assembled dialogue duration is outside tolerance")
    return {
        "schema_version": "1.0",
        "target_seconds": target_seconds,
        "actual_seconds": actual,
        "source_seconds": source_seconds,
        "held_final_frame_seconds": hold_seconds,
        "speaker_count": 2,
        "visible_lip_sync": True,
        "lip_sync_strategy": "partner avatar model generated each speaking shot from its own audio",
        "audio_normalization": {"filter": "EBU R128 loudnorm", "integrated_lufs_target": -16,
                                "true_peak_dbtp_max": -1.5, "loudness_range_lu": 11},
        "clips": [{"path": str(path), "sha256": sha256_file(path)} for path in clips],
        "output": {"path": str(destination), "sha256": sha256_file(destination),
                   "bytes": destination.stat().st_size},
    }


def assemble_master_dialogue_scene(master: str | Path, clips: list[str | Path],
                                   output: str | Path, *, target_seconds: float = 15.0,
                                   master_seconds: float = 3.0) -> dict:
    """Join a silent wide master and three to five synchronized dialogue turns."""
    if not shutil.which("ffmpeg"):
        raise PolicyError("ffmpeg is required for assembly")
    if not 3 <= len(clips) <= 5:
        raise PolicyError("scene assembly requires three to five dialogue turns")
    if not 12.0 <= target_seconds <= 15.0:
        raise PolicyError("scene assembly must be between 12 and 15 seconds")
    if not 2.0 <= master_seconds <= 5.0:
        raise PolicyError("master shot must establish geography for 2–5 seconds")
    master_packet = probe(master)
    if not any(item.get("codec_type") == "video" for item in master_packet.get("streams", [])):
        raise PolicyError("master shot requires a video stream")
    master_duration = float(master_packet.get("format", {}).get("duration", 0))
    if master_duration < master_seconds:
        raise PolicyError("master source is shorter than the requested establishing duration")

    durations: list[float] = []
    for clip in clips:
        packet = probe(clip)
        stream_types = {item.get("codec_type") for item in packet.get("streams", [])}
        if not {"video", "audio"}.issubset(stream_types):
            raise PolicyError("each dialogue turn requires video and audio streams")
        durations.append(float(packet.get("format", {}).get("duration", 0)))
    source_seconds = master_seconds + sum(durations)
    if source_seconds > target_seconds:
        raise PolicyError("master and dialogue turns exceed the target duration")
    hold_seconds = target_seconds - source_seconds

    filters = [
        f"[0:v]trim=duration={master_seconds:.6f},"
        "scale=1280:720:force_original_aspect_ratio=decrease,"
        "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,fps=16,"
        "format=yuv420p,setpts=PTS-STARTPTS[mv]",
        f"anullsrc=r=48000:cl=stereo,atrim=duration={master_seconds:.6f},asetpts=PTS-STARTPTS[ma]",
    ]
    concat_inputs = ["[mv][ma]"]
    for input_index in range(1, len(clips) + 1):
        filters.append(
            f"[{input_index}:v]scale=1280:720:force_original_aspect_ratio=decrease,"
            f"pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,fps=16,"
            f"format=yuv420p,setpts=PTS-STARTPTS[v{input_index}]"
        )
        filters.append(
            f"[{input_index}:a]aresample=48000,"
            f"aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"asetpts=PTS-STARTPTS[a{input_index}]"
        )
        concat_inputs.append(f"[v{input_index}][a{input_index}]")
    filters.append(
        f'{"".join(concat_inputs)}concat=n={len(clips) + 1}:v=1:a=1[cv][ca]'
    )
    filters.append(
        f"[cv]tpad=stop_mode=clone:stop_duration={hold_seconds:.6f},"
        f"trim=duration={target_seconds:.6f}[v]"
    )
    filters.append(
        f"[ca]apad=pad_dur={target_seconds:.6f},atrim=duration={target_seconds:.6f},"
        "loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    )
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = ["ffmpeg", "-y", "-v", "error", "-i", str(master)]
    for clip in clips:
        command.extend(["-i", str(clip)])
    command.extend([
        "-filter_complex", ";".join(filters), "-map", "[v]", "-map", "[a]",
        "-t", f"{target_seconds:.6f}", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-ar", "48000", "-movflags", "+faststart", str(destination),
    ])
    subprocess.run(command, check=True, capture_output=True)
    assembled = probe(destination)
    actual = float(assembled.get("format", {}).get("duration", 0))
    stream_types = {item.get("codec_type") for item in assembled.get("streams", [])}
    if not {"video", "audio"}.issubset(stream_types) or abs(actual - target_seconds) > 0.1:
        raise PolicyError("assembled scene failed stream or duration validation")
    return {
        "schema_version": "1.0",
        "target_seconds": target_seconds,
        "actual_seconds": actual,
        "master_seconds": master_seconds,
        "source_seconds": source_seconds,
        "held_final_frame_seconds": hold_seconds,
        "master_present": True,
        "dialogue_turns": len(clips),
        "visible_lip_sync": True,
        "audio_normalization": {"filter": "EBU R128 loudnorm", "integrated_lufs_target": -16,
                                "true_peak_dbtp_max": -1.5, "loudness_range_lu": 11},
        "master": {"path": str(master), "sha256": sha256_file(master)},
        "clips": [{"path": str(path), "sha256": sha256_file(path)} for path in clips],
        "output": {"path": str(destination), "sha256": sha256_file(destination),
                   "bytes": destination.stat().st_size},
    }


def prepare_dialogue_clip(source: str | Path, output: str | Path, *, start: float,
                          end: float, rate: float, crop: tuple[int, int, int, int]) -> dict:
    """Trim outer silence, preserve sync while pacing, and create a matched 16:9 close-up."""
    if not shutil.which("ffmpeg"):
        raise PolicyError("ffmpeg is required for dialogue preparation")
    packet = probe(source)
    duration = float(packet.get("format", {}).get("duration", 0))
    video = next((item for item in packet.get("streams", [])
                  if item.get("codec_type") == "video"), None)
    if video is None or not any(item.get("codec_type") == "audio"
                                for item in packet.get("streams", [])):
        raise PolicyError("dialogue source requires video and audio")
    if not 0 <= start < end <= duration + 0.01:
        raise PolicyError("dialogue trim must fall within the source duration")
    if not 0.9 <= rate <= 1.25:
        raise PolicyError("dialogue pacing rate must remain between 0.9x and 1.25x")
    crop_width, crop_height, crop_x, crop_y = crop
    source_width = int(video.get("width", 0))
    source_height = int(video.get("height", 0))
    if (crop_width <= 0 or crop_height <= 0 or crop_x < 0 or crop_y < 0 or
            crop_x + crop_width > source_width or crop_y + crop_height > source_height):
        raise PolicyError("dialogue crop falls outside the source frame")
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    filter_graph = (
        f"[0:v]trim=start={start:.6f}:end={end:.6f},setpts=(PTS-STARTPTS)/{rate:.6f},"
        f"crop={crop_width}:{crop_height}:{crop_x}:{crop_y},"
        "scale=1280:720:flags=lanczos,setsar=1,fps=16,format=yuv420p[v];"
        f"[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS,"
        f"atempo={rate:.6f},aresample=48000,"
        "aformat=sample_fmts=fltp:channel_layouts=stereo[a]"
    )
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(source),
        "-filter_complex", filter_graph, "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart",
        str(destination),
    ], check=True, capture_output=True)
    result = probe(destination)
    output_duration = float(result.get("format", {}).get("duration", 0))
    expected = (end - start) / rate
    if abs(output_duration - expected) > 0.1:
        raise PolicyError("prepared dialogue duration is outside tolerance")
    return {
        "schema_version": "1.0",
        "source": {"path": str(source), "sha256": sha256_file(source),
                   "duration_seconds": duration},
        "trim": {"start_seconds": start, "end_seconds": end},
        "pacing_rate": rate,
        "crop": {"width": crop_width, "height": crop_height, "x": crop_x, "y": crop_y},
        "output": {"path": str(destination), "sha256": sha256_file(destination),
                   "bytes": destination.stat().st_size, "duration_seconds": output_duration},
        "sync_preserved": True,
    }


def prepare_stage2_dialogue_clip(source: str | Path, output: str | Path, *, start: float,
                                 end: float, rate: float = 1.0) -> dict:
    """Trim a native 16:9 dialogue take without cropping, padding, or independent AV edits."""
    if not shutil.which("ffmpeg"):
        raise PolicyError("ffmpeg is required for dialogue preparation")
    packet = probe(source)
    facts = native_landscape_facts(packet)
    stream_types = {item.get("codec_type") for item in packet.get("streams", [])}
    duration = float(packet.get("format", {}).get("duration", 0))
    if not facts["native_landscape_16_9"]:
        raise PolicyError("Stage 2 dialogue source must be native square-pixel 16:9 landscape")
    if "audio" not in stream_types:
        raise PolicyError("Stage 2 dialogue source requires synchronized audio")
    if not 0 <= start < end <= duration + 0.01:
        raise PolicyError("dialogue trim must fall within the source duration")
    if not 0.9 <= rate <= 1.1:
        raise PolicyError("Stage 2 dialogue pacing must remain between 0.9x and 1.1x")
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    filters = (
        f"[0:v]trim=start={start:.6f}:end={end:.6f},"
        f"setpts=(PTS-STARTPTS)/{rate:.6f},scale=1280:720:flags=lanczos,"
        "fps=24,format=yuv420p[v];"
        f"[0:a]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS,"
        f"atempo={rate:.6f},aresample=48000,"
        "aformat=sample_fmts=fltp:channel_layouts=stereo[a]"
    )
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(source), "-filter_complex", filters,
        "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium",
        "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-ar", "48000", "-movflags", "+faststart", str(destination),
    ], check=True, capture_output=True)
    result = probe(destination)
    output_duration = float(result.get("format", {}).get("duration", 0))
    expected = (end - start) / rate
    if abs(output_duration - expected) > 0.1:
        raise PolicyError("prepared Stage 2 dialogue duration is outside tolerance")
    return {
        "schema_version": "2.0",
        "source": {"path": str(source), "sha256": sha256_file(source),
                   "duration_seconds": duration, **facts},
        "trim": {"start_seconds": start, "end_seconds": end},
        "pacing_rate": rate,
        "crop": None,
        "padding": None,
        "orientation_repair": None,
        "output": {"path": str(destination), "sha256": sha256_file(destination),
                   "bytes": destination.stat().st_size, "duration_seconds": output_duration},
        "av_transforms_identical": True,
        "generated_lip_sync_claimed": False,
    }


def prepare_stage2_square_dialogue_clip(
        source: str | Path, output: str | Path, *, reference_origin: str | Path,
        start: float, end: float, rate: float, crop: tuple[int, int, int, int]) -> dict:
    """Use the proven square-avatar path while delivering a safe native 16:9 dialogue shot."""
    source_packet = probe(source)
    video = next(
        (item for item in source_packet.get("streams", []) if item.get("codec_type") == "video"),
        None,
    )
    if video is None:
        raise PolicyError("square avatar source requires video")
    source_width = int(video.get("width", 0))
    source_height = int(video.get("height", 0))
    if source_width != source_height or source_width < 512:
        raise PolicyError("Stage 2 square-avatar exception accepts square sources only")
    if str(video.get("sample_aspect_ratio", "1:1")) not in {"1:1", "0:1", "N/A"}:
        raise PolicyError("Stage 2 square-avatar source must use square pixels")
    reference_facts = native_landscape_facts(reference_origin)
    if not reference_facts["native_landscape_16_9"]:
        raise PolicyError("square-avatar reference origin must be an approved native 16:9 scene")
    crop_width, crop_height, _, _ = crop
    if crop_width * 9 != crop_height * 16:
        raise PolicyError("square-avatar crop must be exact 16:9")
    if crop_width < source_width * 0.75 or crop_height < source_height * 0.45:
        raise PolicyError("square-avatar crop is too tight for cinematic dialogue admission")
    if not 0.9 <= rate <= 1.1:
        raise PolicyError("Stage 2 square-avatar pacing must remain between 0.9x and 1.1x")
    base = prepare_dialogue_clip(
        source, output, start=start, end=end, rate=rate, crop=crop,
    )
    output_facts = native_landscape_facts(output)
    if not output_facts["native_landscape_16_9"]:
        raise PolicyError("prepared square-avatar dialogue must be native 16:9")
    return {
        **base,
        "schema_version": "2.1",
        "source_class": "approved_square_avatar_performance",
        "source": {
            **base["source"],
            "width": source_width,
            "height": source_height,
            "sample_aspect_ratio": str(video.get("sample_aspect_ratio", "1:1")),
            "portrait_origin": False,
        },
        "reference_origin": {
            "path": str(reference_origin),
            "sha256": sha256_file(reference_origin),
            **reference_facts,
        },
        "output": {**base["output"], **output_facts},
        "padding": None,
        "orientation_repair": None,
        "av_transforms_identical": True,
        "generated_lip_sync_claimed": False,
        "human_face_mouth_review_required": True,
    }


def generate_room_tone(output: str | Path, *, duration: float,
                       transient_times: list[float] | None = None) -> dict:
    """Generate deterministic, non-verbal interior ambience with optional quiet clicks."""
    if not shutil.which("ffmpeg"):
        raise PolicyError("ffmpeg is required for room tone")
    if not 1.0 <= duration <= 120.0:
        raise PolicyError("room tone duration must be between 1 and 120 seconds")
    transients = transient_times or []
    if any(value < 0 or value >= duration for value in transients):
        raise PolicyError("room-tone transient times must fall inside the duration")

    filters = [
        (f"anoisesrc=color=pink:amplitude=0.012:duration={duration:.6f}:sample_rate=48000,"
         "highpass=f=90,lowpass=f=4200,volume=0.30[bed]"),
    ]
    mix_inputs = ["[bed]"]
    for index, when in enumerate(transients):
        delay_ms = round(when * 1000)
        filters.append(
            "sine=frequency=1150:sample_rate=48000:duration=0.035,"
            f"afade=t=out:st=0:d=0.035,volume=0.025,adelay={delay_ms}:all=1[c{index}]"
        )
        mix_inputs.append(f"[c{index}]")
    filters.append(
        f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=longest:normalize=0,"
        f"atrim=duration={duration:.6f},aformat=sample_fmts=fltp:channel_layouts=stereo[a]"
    )
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-filter_complex", ";".join(filters),
        "-map", "[a]", "-c:a", "pcm_s16le", "-ar", "48000", str(destination),
    ], check=True, capture_output=True)
    packet = probe(destination)
    actual = float(packet.get("format", {}).get("duration", 0))
    if abs(actual - duration) > 0.05:
        raise PolicyError("generated room tone duration is outside tolerance")
    return {
        "schema_version": "1.0",
        "kind": "deterministic_nonverbal_room_tone",
        "duration_seconds": actual,
        "transient_times_seconds": transients,
        "contains_intelligible_speech": False,
        "output": {"path": str(destination), "sha256": sha256_file(destination),
                   "bytes": destination.stat().st_size},
    }


def generate_clinic_ambience(output: str | Path, *, duration: float,
                              fade_seconds: float = 0.5) -> dict:
    """Create honest non-speech mechanical clinic room tone.

    Human chatter must be supplied from independent speech/field-recording assets; procedural
    noise is never labelled or promoted as people talking.
    """
    if not shutil.which("ffmpeg"):
        raise PolicyError("ffmpeg is required for ambience generation")
    if not 12.0 <= duration <= 90.0:
        raise PolicyError("clinic ambience duration must be between 12 and 90 seconds")
    if not 0.25 <= fade_seconds <= 1.0 or fade_seconds * 2 >= duration:
        raise PolicyError("ambience fade must be 0.25–1.0 seconds and fit the duration")
    fade_out = duration - fade_seconds
    filter_graph = (
        f"sine=frequency=58:sample_rate=48000:duration={duration:.6f},volume=0.10[hvac];"
        f"sine=frequency=116:sample_rate=48000:duration={duration:.6f},volume=0.032[mechanical];"
        f"[hvac][mechanical]amix=inputs=2:duration=longest:normalize=0,"
        f"afade=t=in:st=0:d={fade_seconds:.6f},"
        f"afade=t=out:st={fade_out:.6f}:d={fade_seconds:.6f},"
        f"atrim=duration={duration:.6f},aformat=sample_fmts=fltp:channel_layouts=stereo[a]"
    )
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-filter_complex", filter_graph,
        "-map", "[a]", "-c:a", "pcm_s16le", "-ar", "48000", str(destination),
    ], check=True, capture_output=True)
    actual = float(probe(destination).get("format", {}).get("duration", 0))
    if abs(actual - duration) > 0.05:
        raise PolicyError("generated clinic ambience duration is outside tolerance")
    return {
        "schema_version": "2.0",
        "kind": "clinic_ambience_bed",
        "duration_seconds": actual,
        "fade_in_seconds": fade_seconds,
        "fade_out_seconds": fade_seconds,
        "contains_intelligible_speech": False,
        "components": ["restrained low HVAC fundamental", "soft mechanical harmonic"],
        "output": {"path": str(destination), "sha256": sha256_file(destination),
                   "bytes": destination.stat().st_size},
    }


def assemble_timeline(intervals: list[dict], output: str | Path, *,
                      ambience: str | Path | None = None,
                      target_seconds: float | None = None,
                      native_landscape_only: bool = False,
                      require_typed_lineage: bool = False,
                      allow_holds: bool = True,
                      fade_seconds: float = 0.0,
                      ambience_volume: float = 0.24) -> dict:
    """Assemble independently replaceable AV intervals while preserving sync and provenance."""
    if not shutil.which("ffmpeg"):
        raise PolicyError("ffmpeg is required for timeline assembly")
    if not 4 <= len(intervals) <= 32:
        raise PolicyError("timeline requires 4–32 intervals")

    normalized: list[dict] = []
    for index, raw in enumerate(intervals):
        source = Path(raw.get("path", ""))
        if not source.is_file():
            raise PolicyError(f"timeline source {index} does not exist")
        packet = probe(source)
        stream_types = {item.get("codec_type") for item in packet.get("streams", [])}
        if "video" not in stream_types:
            raise PolicyError(f"timeline source {index} has no video")
        facts = native_landscape_facts(packet)
        if native_landscape_only and not facts["native_landscape_16_9"]:
            raise PolicyError(f"timeline source {index} is not native square-pixel 16:9 landscape")
        if require_typed_lineage:
            required_lineage = {
                "series_id", "season_id", "episode_id", "sequence_id", "scene_id", "setup_id",
                "take_id", "clip_id", "shot_id", "transition_after", "generation_source_path",
                "generation_request_id", "persona_versions", "transition_id", "cut_after_id",
            }
            missing_lineage = required_lineage - raw.keys()
            if missing_lineage:
                raise PolicyError(
                    f"timeline source {index} missing typed lineage: "
                    f"{', '.join(sorted(missing_lineage))}"
                )
            if not str(raw["generation_request_id"]).strip():
                raise PolicyError(f"timeline source {index} has no generation_request_id")
            if not isinstance(raw["persona_versions"], dict) or not raw["persona_versions"]:
                raise PolicyError(f"timeline source {index} has no persona_versions mapping")
            if not re.fullmatch(r"trn-?[0-9a-z][0-9a-z-]*", str(raw["transition_id"])):
                raise PolicyError(f"timeline source {index} has invalid transition_id")
            if raw["transition_after"] == "cut":
                if not re.fullmatch(r"cut-?[0-9a-z][0-9a-z-]*", str(raw["cut_after_id"])):
                    raise PolicyError(f"timeline source {index} cut has invalid cut_after_id")
            elif raw["cut_after_id"] is not None:
                raise PolicyError(f"timeline source {index} non-cut transition has cut_after_id")
            generation_source = Path(str(raw["generation_source_path"]))
            if not generation_source.is_file():
                raise PolicyError(f"timeline source {index} generation source does not exist")
            generation_facts = native_landscape_facts(generation_source)
            if not generation_facts["native_landscape_16_9"]:
                raise PolicyError(
                    f"timeline source {index} originated from non-native 16:9 media"
                )
        else:
            generation_source = source
            generation_facts = facts
        source_duration = float(packet.get("format", {}).get("duration", 0))
        start = float(raw.get("start", 0.0))
        end = float(raw.get("end", source_duration))
        rate = float(raw.get("rate", 1.0))
        hold = float(raw.get("hold_after", 0.0))
        if not 0 <= start < end <= source_duration + 0.02:
            raise PolicyError(f"timeline trim {index} falls outside its source")
        if not 0.9 <= rate <= 1.25:
            raise PolicyError(f"timeline rate {index} must remain between 0.9x and 1.25x")
        if not 0 <= hold <= 5.0:
            raise PolicyError(f"timeline hold {index} must be between 0 and 5 seconds")
        if not allow_holds and hold:
            raise PolicyError(f"timeline source {index} uses a forbidden Stage 2 freeze hold")
        include_audio = bool(raw.get("include_audio", "audio" in stream_types))
        if include_audio and "audio" not in stream_types:
            raise PolicyError(f"timeline source {index} was marked for audio but has none")
        duration = (end - start) / rate + hold
        normalized.append({**raw, "path": str(source), "start": start, "end": end,
                           "rate": rate, "hold_after": hold, "include_audio": include_audio,
                           "source_duration": source_duration, "duration": duration,
                           "native_facts": facts})

    computed_seconds = sum(item["duration"] for item in normalized)
    target = computed_seconds if target_seconds is None else float(target_seconds)
    if not 12.0 <= target <= 90.0:
        raise PolicyError("timeline duration must be between 12 and 90 seconds")
    if abs(computed_seconds - target) > 0.05:
        raise PolicyError("timeline intervals do not sum to the target duration")
    if fade_seconds < 0 or fade_seconds * 2 >= target:
        raise PolicyError("timeline fades must be non-negative and fit the duration")
    if not 0 <= ambience_volume <= 2.0:
        raise PolicyError("ambience volume must be between 0 and 2")
    if ambience is not None:
        ambience_path = Path(ambience)
        if not ambience_path.is_file():
            raise PolicyError("timeline ambience does not exist")
        ambience_packet = probe(ambience_path)
        if not any(item.get("codec_type") == "audio"
                   for item in ambience_packet.get("streams", [])):
            raise PolicyError("timeline ambience has no audio stream")
        if float(ambience_packet.get("format", {}).get("duration", 0)) + 0.05 < target:
            raise PolicyError("timeline ambience is shorter than the timeline")

    command = ["ffmpeg", "-y", "-v", "error"]
    for item in normalized:
        command.extend(["-i", item["path"]])
    if ambience is not None:
        command.extend(["-i", str(ambience)])

    filters: list[str] = []
    concat_inputs: list[str] = []
    cursor = 0.0
    provenance: list[dict] = []
    for index, item in enumerate(normalized):
        clip_duration = (item["end"] - item["start"]) / item["rate"]
        hold = item["hold_after"]
        scale = (
            "scale=1280:720:flags=lanczos,fps=24,format=yuv420p"
            if native_landscape_only else
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,fps=16,format=yuv420p"
        )
        filters.append(
            f"[{index}:v]trim=start={item['start']:.6f}:end={item['end']:.6f},"
            f"setpts=(PTS-STARTPTS)/{item['rate']:.6f},{scale},"
            f"tpad=stop_mode=clone:stop_duration={hold:.6f}[v{index}]"
        )
        if item["include_audio"]:
            filters.append(
                f"[{index}:a]atrim=start={item['start']:.6f}:end={item['end']:.6f},"
                f"asetpts=PTS-STARTPTS,atempo={item['rate']:.6f},aresample=48000,"
                "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"apad=pad_dur={hold:.6f},atrim=duration={item['duration']:.6f}[a{index}]"
            )
        else:
            filters.append(
                f"anullsrc=r=48000:cl=stereo,atrim=duration={item['duration']:.6f},"
                f"asetpts=PTS-STARTPTS[a{index}]"
            )
        concat_inputs.append(f"[v{index}][a{index}]")
        interval_out = cursor + item["duration"]
        provenance.append({
            "interval_id": item.get("id", f"interval-{index + 1:02d}"),
            "scene_id": item.get("scene_id"),
            "shot_id": item.get("shot_id"),
            "timeline_in_seconds": round(cursor, 6),
            "timeline_out_seconds": round(interval_out, 6),
            "source": {"path": item["path"], "sha256": sha256_file(item["path"]),
                       "duration_seconds": item["source_duration"], **item["native_facts"]},
            "generation_source": {
                "path": str(item["generation_source_path"]),
                "sha256": sha256_file(item["generation_source_path"]),
                **native_landscape_facts(item["generation_source_path"]),
            } if require_typed_lineage else None,
            "source_trim": {"start_seconds": item["start"], "end_seconds": item["end"],
                            "rate": item["rate"], "held_after_seconds": hold},
            "audio_included": item["include_audio"],
            "sync_locked": bool(item.get("sync_locked", item["include_audio"])),
            "source_role": item.get("source_role"),
            "audit_decision": item.get("audit_decision"),
            "audit_reference": item.get("audit_reference"),
            "series_id": item.get("series_id"),
            "season_id": item.get("season_id"),
            "episode_id": item.get("episode_id"),
            "sequence_id": item.get("sequence_id"),
            "setup_id": item.get("setup_id"),
            "take_id": item.get("take_id"),
            "clip_id": item.get("clip_id"),
            "persona_version": item.get("persona_version"),
            "persona_versions": item.get("persona_versions"),
            "generation_request_id": item.get("generation_request_id"),
            "transition_after": item.get("transition_after"),
            "transition_id": item.get("transition_id"),
            "cut_after_id": item.get("cut_after_id"),
        })
        cursor = interval_out
    filters.append(
        f"{''.join(concat_inputs)}concat=n={len(normalized)}:v=1:a=1[cv][ca]"
    )
    video_tail = f"[cv]trim=duration={target:.6f},setpts=PTS-STARTPTS"
    if fade_seconds:
        video_tail += (f",fade=t=in:st=0:d={fade_seconds:.6f},"
                       f"fade=t=out:st={target - fade_seconds:.6f}:d={fade_seconds:.6f}")
    filters.append(f"{video_tail}[v]")
    if ambience is not None:
        ambience_index = len(normalized)
        filters.append(
            f"[{ambience_index}:a]atrim=duration={target:.6f},asetpts=PTS-STARTPTS,"
            "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"volume={ambience_volume:.6f}[amb]"
        )
        audio_tail = (f"[ca][amb]amix=inputs=2:duration=first:normalize=0,"
                      f"atrim=duration={target:.6f},loudnorm=I=-16:TP=-1.5:LRA=11")
    else:
        audio_tail = f"[ca]atrim=duration={target:.6f},loudnorm=I=-16:TP=-1.5:LRA=11"
    if fade_seconds:
        audio_tail += (f",afade=t=in:st=0:d={fade_seconds:.6f},"
                       f"afade=t=out:st={target - fade_seconds:.6f}:d={fade_seconds:.6f}")
    filters.append(f"{audio_tail}[a]")

    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    command.extend([
        "-filter_complex", ";".join(filters), "-map", "[v]", "-map", "[a]",
        "-t", f"{target:.6f}", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart", str(destination),
    ])
    subprocess.run(command, check=True, capture_output=True)
    assembled = probe(destination)
    actual = float(assembled.get("format", {}).get("duration", 0))
    stream_types = {item.get("codec_type") for item in assembled.get("streams", [])}
    if not {"video", "audio"}.issubset(stream_types) or abs(actual - target) > 0.1:
        raise PolicyError("assembled timeline failed stream or duration validation")
    return {
        "schema_version": "2.0",
        "target_seconds": target,
        "actual_seconds": actual,
        "interval_count": len(normalized),
        "sync_policy": "source audio and picture share identical trims and rate transforms",
        "native_landscape_only": native_landscape_only,
        "typed_lineage_required": require_typed_lineage,
        "freeze_holds_allowed": allow_holds,
        "fade_in_seconds": fade_seconds,
        "fade_out_seconds": fade_seconds,
        "audio_normalization": {"filter": "EBU R128 loudnorm", "integrated_lufs_target": -16,
                                "true_peak_dbtp_max": -1.5, "loudness_range_lu": 11},
        "ambience": ({"path": str(ambience), "sha256": sha256_file(ambience)}
                     if ambience is not None else None),
        "ambience_volume": ambience_volume if ambience is not None else None,
        "provenance": provenance,
        "output": {"path": str(destination), "sha256": sha256_file(destination),
                   "bytes": destination.stat().st_size},
    }


def assemble_stage2_timeline(intervals: list[dict], output: str | Path, *,
                             ambience: str | Path, target_seconds: float,
                             fade_seconds: float = 0.5,
                             ambience_volume: float = 1.0) -> dict:
    """Assemble a Stage 2 sequence while refusing portrait wrappers, freezes, and weak lineage."""
    return assemble_timeline(
        intervals, output, ambience=ambience, target_seconds=target_seconds,
        native_landscape_only=True, require_typed_lineage=True, allow_holds=False,
        fade_seconds=fade_seconds, ambience_volume=ambience_volume,
    )
