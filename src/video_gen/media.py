from __future__ import annotations

import hashlib
import json
import math
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


def contact_sheet(video: str | Path, output: str | Path) -> None:
    if not shutil.which("ffmpeg"):
        raise PolicyError("ffmpeg is required for contact sheets")
    duration = float(probe(video).get("format", {}).get("duration", 0))
    rows = max(1, math.ceil(max(duration, 1) / 5))
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
        "scale=1280:720:flags=lanczos,fps=16,format=yuv420p[v];"
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


def assemble_timeline(intervals: list[dict], output: str | Path, *,
                      ambience: str | Path | None = None,
                      target_seconds: float | None = None) -> dict:
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
        include_audio = bool(raw.get("include_audio", "audio" in stream_types))
        if include_audio and "audio" not in stream_types:
            raise PolicyError(f"timeline source {index} was marked for audio but has none")
        duration = (end - start) / rate + hold
        normalized.append({**raw, "path": str(source), "start": start, "end": end,
                           "rate": rate, "hold_after": hold, "include_audio": include_audio,
                           "source_duration": source_duration, "duration": duration})

    computed_seconds = sum(item["duration"] for item in normalized)
    target = computed_seconds if target_seconds is None else float(target_seconds)
    if not 12.0 <= target <= 90.0:
        raise PolicyError("timeline duration must be between 12 and 90 seconds")
    if abs(computed_seconds - target) > 0.05:
        raise PolicyError("timeline intervals do not sum to the target duration")
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
        filters.append(
            f"[{index}:v]trim=start={item['start']:.6f}:end={item['end']:.6f},"
            f"setpts=(PTS-STARTPTS)/{item['rate']:.6f},"
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,fps=16,format=yuv420p,"
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
                       "duration_seconds": item["source_duration"]},
            "source_trim": {"start_seconds": item["start"], "end_seconds": item["end"],
                            "rate": item["rate"], "held_after_seconds": hold},
            "audio_included": item["include_audio"],
            "sync_locked": bool(item.get("sync_locked", item["include_audio"])),
            "source_role": item.get("source_role"),
            "audit_decision": item.get("audit_decision"),
            "audit_reference": item.get("audit_reference"),
        })
        cursor = interval_out
    filters.append(
        f"{''.join(concat_inputs)}concat=n={len(normalized)}:v=1:a=1[cv][ca]"
    )
    filters.append(f"[cv]trim=duration={target:.6f},setpts=PTS-STARTPTS[v]")
    if ambience is not None:
        ambience_index = len(normalized)
        filters.append(
            f"[{ambience_index}:a]atrim=duration={target:.6f},asetpts=PTS-STARTPTS,"
            "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            "volume=0.24[amb]"
        )
        filters.append(
            f"[ca][amb]amix=inputs=2:duration=first:normalize=0,"
            f"atrim=duration={target:.6f},loudnorm=I=-16:TP=-1.5:LRA=11[a]"
        )
    else:
        filters.append(
            f"[ca]atrim=duration={target:.6f},loudnorm=I=-16:TP=-1.5:LRA=11[a]"
        )

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
        "audio_normalization": {"filter": "EBU R128 loudnorm", "integrated_lufs_target": -16,
                                "true_peak_dbtp_max": -1.5, "loudness_range_lu": 11},
        "ambience": ({"path": str(ambience), "sha256": sha256_file(ambience)}
                     if ambience is not None else None),
        "provenance": provenance,
        "output": {"path": str(destination), "sha256": sha256_file(destination),
                   "bytes": destination.stat().st_size},
    }
