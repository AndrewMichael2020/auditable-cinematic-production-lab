from __future__ import annotations

import json
import re
import wave
from pathlib import Path
from typing import Any

from .errors import PolicyError
from .media import sha256_file


def _load_object(path: str | Path, context: str) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PolicyError(f"{context} must be a JSON object")
    return value


def _word_tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?", value.lower())


def _audited_turn_boundaries(
    asr_audit: str | Path,
    turns: list[dict[str, Any]],
    audio_seconds: float,
) -> list[dict[str, float]]:
    """Align exact scripted words to ASR words and cut only inside inter-line gaps."""
    packet = _load_object(asr_audit, "dialogue ASR audit")
    words = packet.get("words")
    if not isinstance(words, list) or not words:
        raise PolicyError("dialogue ASR audit requires word timestamps")
    observed: list[tuple[str, float, float]] = []
    for item in words:
        if not isinstance(item, dict):
            raise PolicyError("dialogue ASR words must be objects")
        tokens = _word_tokens(str(item.get("word", "")))
        if len(tokens) != 1:
            raise PolicyError("each dialogue ASR word must normalize to one token")
        start = float(item.get("start", -1))
        end = float(item.get("end", -1))
        if not 0 <= start < end <= audio_seconds + 0.05:
            raise PolicyError("dialogue ASR word timestamp is outside source audio")
        observed.append((tokens[0], start, min(end, audio_seconds)))

    cursor = 0
    speech_spans: list[tuple[float, float]] = []
    observed_tokens = [item[0] for item in observed]
    for turn in turns:
        expected = _word_tokens(str(turn.get("line", "")))
        if not expected:
            raise PolicyError("dialogue turn line has no alignable words")
        match = next(
            (
                index
                for index in range(cursor, len(observed) - len(expected) + 1)
                if observed_tokens[index:index + len(expected)] == expected
            ),
            None,
        )
        if match is None:
            raise PolicyError(
                f"dialogue ASR words do not contain scripted line: {turn.get('dialogue_id')}"
            )
        final_word = match + len(expected) - 1
        speech_spans.append((observed[match][1], observed[final_word][2]))
        cursor = final_word + 1

    boundaries: list[dict[str, float]] = []
    for index, (speech_start, speech_end) in enumerate(speech_spans):
        start = (
            0.0 if index == 0
            else (speech_spans[index - 1][1] + speech_start) / 2
        )
        end = (
            audio_seconds if index == len(speech_spans) - 1
            else (speech_end + speech_spans[index + 1][0]) / 2
        )
        if not 0 <= start < speech_start < speech_end <= end <= audio_seconds + 0.01:
            raise PolicyError("dialogue ASR alignment produced invalid turn boundaries")
        boundaries.append({
            "start": start,
            "end": min(end, audio_seconds),
            "speech_start": speech_start,
            "speech_end": speech_end,
        })
    return boundaries


def prepare_dialogue_turns(
    candidate_audio: str | Path,
    candidate_manifest: str | Path,
    voice_plan: str | Path,
    output_dir: str | Path,
    *,
    lead_in_seconds: float = 0.35,
    asr_audit: str | Path | None = None,
) -> dict[str, Any]:
    """Split one timestamped PCM dialogue candidate into shot-length WAV files.

    The performance audio is never stretched. Each turn receives deterministic silence
    before and after the source segment so a video model can use an exact storyboard
    duration without changing pitch, pace, or persona performance.
    """
    if not 0 <= lead_in_seconds <= 1:
        raise PolicyError("dialogue lead-in must be between zero and one second")
    audio_path = Path(candidate_audio)
    if not audio_path.is_file():
        raise PolicyError("dialogue candidate audio is missing")
    manifest = _load_object(candidate_manifest, "dialogue candidate manifest")
    plan = _load_object(voice_plan, "voice plan")
    turns = manifest.get("turns")
    segments = manifest.get("voice_segments")
    if not isinstance(turns, list) or not isinstance(segments, list):
        raise PolicyError("dialogue candidate requires turns and voice_segments")
    if not turns or len(turns) != len(segments):
        raise PolicyError("dialogue turns and voice segments must align")
    target_by_dialogue_id = {
        str(beat["dialogue_id"]): float(beat["seconds"])
        for beat in plan.get("beats", [])
        if isinstance(beat, dict) and beat.get("speaker")
    }
    if set(target_by_dialogue_id) != {
        str(turn.get("dialogue_id", "")) for turn in turns if isinstance(turn, dict)
    }:
        raise PolicyError("voice plan and dialogue candidate turns do not match")

    destination_dir = Path(output_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    prepared: list[dict[str, Any]] = []
    with wave.open(str(audio_path), "rb") as source:
        channels = source.getnchannels()
        sample_width = source.getsampwidth()
        sample_rate = source.getframerate()
        compression = source.getcomptype()
        total_frames = source.getnframes()
        if compression != "NONE" or sample_width not in {1, 2, 3, 4}:
            raise PolicyError("dialogue candidate must be uncompressed PCM WAV")
        frame_size = channels * sample_width
        all_frames = source.readframes(total_frames)
    audio_seconds = total_frames / sample_rate
    audited_boundaries = (
        _audited_turn_boundaries(asr_audit, turns, audio_seconds)
        if asr_audit is not None else None
    )

    for index, (turn, segment) in enumerate(zip(turns, segments, strict=True)):
        if not isinstance(turn, dict) or not isinstance(segment, dict):
            raise PolicyError("dialogue turn metadata must be objects")
        if int(segment.get("dialogue_input_index", -1)) != index:
            raise PolicyError("dialogue segment order does not match candidate input order")
        dialogue_id = str(turn.get("dialogue_id", "")).strip()
        provider_start = float(segment.get("start_time_seconds", -1))
        provider_end = float(segment.get("end_time_seconds", -1))
        if not 0 <= provider_start < provider_end <= audio_seconds + 0.01:
            raise PolicyError(f"dialogue segment is outside source audio: {dialogue_id}")
        if audited_boundaries is not None:
            boundary = audited_boundaries[index]
            start = boundary["start"]
            end = boundary["end"]
        else:
            start = provider_start
            # Provider turn timestamps can end before the final audible phonemes. The
            # last turn has no following speaker to protect, so it owns the remainder.
            end = audio_seconds if index == len(turns) - 1 else provider_end
        target = target_by_dialogue_id[dialogue_id]
        if audited_boundaries is not None and end - start + lead_in_seconds > target:
            speech_start = audited_boundaries[index]["speech_start"]
            speech_end = audited_boundaries[index]["speech_end"]
            available = target - lead_in_seconds
            speech_seconds = speech_end - speech_start
            if speech_seconds > available + 1 / sample_rate:
                raise PolicyError(
                    f"audited dialogue speech exceeds storyboard duration: {dialogue_id}"
                )
            margin = max(0.0, available - speech_seconds)
            pre_gap = speech_start - start
            post_gap = end - speech_end
            pre = min(pre_gap, margin / 2)
            post = min(post_gap, margin - pre)
            pre += min(pre_gap - pre, margin - pre - post)
            post += min(post_gap - post, margin - pre - post)
            start = speech_start - pre
            end = speech_end + post
        source_seconds = end - start
        if source_seconds + lead_in_seconds > target + 1 / sample_rate:
            raise PolicyError(f"dialogue segment exceeds storyboard duration: {dialogue_id}")
        start_frame = round(start * sample_rate)
        end_frame = min(total_frames, round(end * sample_rate))
        source_bytes = all_frames[start_frame * frame_size:end_frame * frame_size]
        target_frames = round(target * sample_rate)
        lead_frames = round(lead_in_seconds * sample_rate)
        source_frames = len(source_bytes) // frame_size
        tail_frames = target_frames - lead_frames - source_frames
        if tail_frames < 0:
            raise PolicyError(f"dialogue padding calculation overflowed: {dialogue_id}")
        silence_frame = b"\x00" * frame_size
        output = destination_dir / f"{index + 1:02d}-{dialogue_id}.wav"
        if output.exists():
            raise PolicyError(f"dialogue turn destination already exists: {output}")
        with wave.open(str(output), "wb") as destination:
            destination.setnchannels(channels)
            destination.setsampwidth(sample_width)
            destination.setframerate(sample_rate)
            destination.writeframes(silence_frame * lead_frames)
            destination.writeframes(source_bytes)
            destination.writeframes(silence_frame * tail_frames)
        prepared.append({
            "dialogue_id": dialogue_id,
            "speaker": turn.get("speaker"),
            "voice_persona_id": turn.get("voice_persona_id"),
            "voice_realization_id": turn.get("voice_realization_id"),
            "line": turn.get("line"),
            "source_start_seconds": start,
            "source_end_seconds": end,
            "provider_reported_start_seconds": provider_start,
            "provider_reported_end_seconds": provider_end,
            "source_end_extended_to_audio_end": end > provider_end + 1 / sample_rate,
            "asr_speech_start_seconds": (
                audited_boundaries[index]["speech_start"]
                if audited_boundaries is not None else None
            ),
            "asr_speech_end_seconds": (
                audited_boundaries[index]["speech_end"]
                if audited_boundaries is not None else None
            ),
            "source_duration_seconds": source_seconds,
            "lead_in_seconds": lead_frames / sample_rate,
            "tail_seconds": tail_frames / sample_rate,
            "target_seconds": target,
            "output_path": str(output),
            "output_sha256": sha256_file(output),
        })

    report = {
        "schema_version": "1.0",
        "artifact_type": "prepared_dialogue_turns",
        "candidate_id": manifest.get("candidate_id"),
        "source_audio": {
            "path": str(audio_path),
            "sha256": sha256_file(audio_path),
            "sample_rate": sample_rate,
            "channels": channels,
            "sample_width_bytes": sample_width,
        },
        "preservation": {
            "speech_stretched": False,
            "speech_resampled": False,
            "padding_only": True,
            "boundary_source": (
                "audited_asr_word_gaps" if audited_boundaries is not None
                else "provider_turn_timestamps_with_final_audio_tail"
            ),
        },
        "asr_audit": str(asr_audit) if asr_audit is not None else None,
        "turns": prepared,
    }
    report_path = destination_dir / "prepared-dialogue-turns.manifest.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
