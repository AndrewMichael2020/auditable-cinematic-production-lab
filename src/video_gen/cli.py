from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import os
import sys
from decimal import Decimal
from pathlib import Path

from .auditor import (audit_continuity, audit_draft, audit_final_candidate, audit_scene,
                      text_sha256,
                      verify_bounded_repair_authorization, verify_promotion_authorization,
                      verify_storyboard_authorization)
from .av_sync import audit_av_sync_file
from .config import ProjectConfig
from .elevenlabs import ElevenLabsClient
from .dialogue_turns import prepare_dialogue_turns
from .errors import VideoGenError
from .ledger import Ledger
from .media import (assemble_lipsynced_dialogue, assemble_master_dialogue_scene,
                    assemble_stage2_timeline, assemble_timeline, assemble_with_audio,
                    contact_sheet, generate_clinic_ambience, generate_room_tone,
                    prepare_dialogue_clip, prepare_stage2_dialogue_clip,
                    prepare_stage2_square_dialogue_clip)
from .orchestrator import Orchestrator
from .production import compile_prompt, load_production, load_scene
from .retention import (audit_run_artifacts, prune_recomputable_artifacts,
                        prune_rejected_media)
from .stage2 import (audit_stage2_sequence, compile_stage2_prompt,
                     compile_stage2_take_prompt,
                     load_series, load_stage2_sequence)
from .voice_personas import (load_voice_plan, voice_audition_spec,
                             dialogue_candidate_spec,
                             voice_budget_report, voice_readiness_report)
from .voice_casting import rank_voice_catalog


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="video-gen")
    result.add_argument("--config", default="project.json")
    result.add_argument("--ledger", default="runs/ledger.sqlite3")
    result.add_argument("--run-cap-usd", type=Decimal)
    result.add_argument("--partner-avatar-attempt-cap", type=int, default=5)
    commands = result.add_subparsers(dest="command", required=True)
    preflight = commands.add_parser("preflight", help="validate configuration without spending")
    preflight.add_argument("--profile", default="cad_10")
    preflight.add_argument("--output")
    validate = commands.add_parser("validate-scene", help="validate and compile the golden scene")
    validate.add_argument("scene", nargs="?", default="scenes/golden-scene.json")
    validate.add_argument("--output")
    validate_production = commands.add_parser(
        "validate-production", help="validate an ordered, independently resumable production")
    validate_production.add_argument("production")
    validate_stage2 = commands.add_parser(
        "validate-stage2", help="validate and compile a typed Stage 2 sequence package")
    validate_stage2.add_argument("sequence")
    validate_stage2.add_argument("--output")
    validate_voice = commands.add_parser(
        "validate-voice-plan",
        help="validate canonical voice-persona lineage and report readiness",
    )
    validate_voice.add_argument("plan")
    validate_voice.add_argument("--output")
    audit_stage2 = commands.add_parser(
        "audit-stage2", help="audit Stage 2 lineage, native format, edit rhythm, sound, and human gates")
    audit_stage2.add_argument("--sequence", required=True)
    audit_stage2.add_argument("--timeline", required=True)
    audit_stage2.add_argument("--final")
    audit_stage2.add_argument("--observations")
    audit_stage2.add_argument("--output")
    audit_storyboard = commands.add_parser("audit-scene", help="run the pre-generation spatial gate")
    audit_storyboard.add_argument("scene", nargs="?", default="scenes/golden-scene.json")
    audit_storyboard.add_argument("--output")
    audit_media = commands.add_parser("audit-draft", help="build or evaluate a cheap-draft audit")
    audit_media.add_argument("video")
    audit_media.add_argument("--scene", default="scenes/golden-scene.json")
    audit_media.add_argument("--shot", required=True)
    audit_media.add_argument("--observations")
    audit_media.add_argument("--contact-sheet")
    audit_media.add_argument("--output")
    audit_stage = commands.add_parser("audit-stage", help="run a staged media or continuity audit")
    audit_stage.add_argument("--stage", choices=["cheap_draft", "final_candidate",
                                                  "cross_shot_continuity",
                                                  "cross_scene_continuity", "final_sequence"],
                             required=True)
    audit_stage.add_argument("--scene", required=True)
    audit_stage.add_argument("--shot")
    audit_stage.add_argument("--video")
    audit_stage.add_argument("--observations", required=True)
    audit_stage.add_argument("--contact-sheet")
    audit_stage.add_argument("--output")
    plan = commands.add_parser("plan-video", help="reserve and print a dry-run video request")
    plan.add_argument("--profile", default="cad_10")
    plan.add_argument(
        "--role",
        choices=["final_video", "cosmos_world_video"],
        required=True,
    )
    prompt_source = plan.add_mutually_exclusive_group(required=True)
    prompt_source.add_argument("--prompt")
    prompt_source.add_argument("--prompt-file")
    prompt_source.add_argument("--scene-manifest")
    plan.add_argument("--seed", type=int, default=0)
    plan.add_argument(
        "--image",
        help="optional local image or public HTTPS image for Cosmos I2V conditioning",
    )
    plan.add_argument("--live", action="store_true")
    plan.add_argument("--confirm-live", action="store_true")
    plan.add_argument("--scene-audit")
    plan.add_argument("--shot-id")
    plan.add_argument("--draft-audit")
    plan.add_argument("--repair-authorization")
    plan.add_argument("--result")
    plan.add_argument("--output-dir", default="outputs")
    plan.add_argument("--webhook-url")
    plan.add_argument("--webhook-result")
    plan.add_argument("--webhook-wait-seconds", type=float, default=900)
    image_video = commands.add_parser(
        "plan-image-video",
        help="animate one approved storyboard plate through the bounded Stage 2 partner exception",
    )
    image_video.add_argument("--profile", default="cad_10")
    image_video.add_argument("--image", required=True)
    image_video.add_argument("--audio")
    image_video.add_argument("--prompt-file", required=True)
    image_video.add_argument("--seed", type=int, default=0)
    image_video.add_argument("--seconds", type=int, default=5)
    image_video.add_argument("--output-dir", default="outputs")
    image_video.add_argument("--allow-partner-i2v", action="store_true")
    image_video.add_argument(
        "--inline-local-assets",
        action="store_true",
        help="embed bounded local image/audio data directly in the provider request",
    )
    image_video.add_argument("--live", action="store_true")
    image_video.add_argument("--confirm-live", action="store_true")
    image_video.add_argument("--scene-audit")
    image_video.add_argument("--take-id")
    image_video.add_argument("--repair-authorization")
    image_video.add_argument("--result")
    image_video.add_argument("--webhook-url")
    image_video.add_argument("--webhook-result")
    image_video.add_argument("--webhook-wait-seconds", type=float, default=900)
    speech = commands.add_parser("plan-speech", help="reserve or generate one bounded speech line")
    speech.add_argument("--profile", default="cad_10")
    speech.add_argument("--text", required=True)
    speech.add_argument("--seed", type=int, default=0)
    speech.add_argument("--series-manifest")
    speech.add_argument("--character-id")
    speech.add_argument("--live", action="store_true")
    speech.add_argument("--confirm-live", action="store_true")
    speech.add_argument("--result")
    voice_audition = commands.add_parser(
        "plan-voice-audition",
        help="reserve or generate one canonical persona audition/performance master",
    )
    voice_audition.add_argument("--profile", default="cad_10")
    voice_audition.add_argument("--plan", required=True)
    voice_audition.add_argument("--character", required=True)
    voice_audition.add_argument("--output-dir", default="outputs")
    voice_audition.add_argument("--live", action="store_true")
    voice_audition.add_argument("--confirm-live", action="store_true")
    voice_audition.add_argument("--result")
    voice_match = commands.add_parser(
        "match-voices",
        help="rank the current ElevenLabs voice catalog against one persona contract",
    )
    voice_match.add_argument("--plan", required=True)
    voice_match.add_argument("--character", required=True)
    voice_match.add_argument(
        "--catalog",
        help="optional cached ElevenLabs voices JSON; otherwise fetch the live read-only catalog",
    )
    voice_match.add_argument("--top", type=int, default=5)
    voice_match.add_argument("--output")
    dialogue_candidate = commands.add_parser(
        "plan-dialogue-candidate",
        help="reserve or generate one timestamped multi-speaker ElevenLabs candidate",
    )
    dialogue_candidate.add_argument("--profile", default="cad_10")
    dialogue_candidate.add_argument("--plan", required=True)
    dialogue_candidate.add_argument("--output-dir", default="outputs")
    dialogue_candidate.add_argument("--live", action="store_true")
    dialogue_candidate.add_argument("--confirm-live", action="store_true")
    dialogue_candidate.add_argument("--result")
    dialogue_turns = commands.add_parser(
        "prepare-dialogue-turns",
        help="split a timestamped dialogue candidate into padded storyboard-length WAV files",
    )
    dialogue_turns.add_argument("--profile", default="cad_10")
    dialogue_turns.add_argument("--audio", required=True)
    dialogue_turns.add_argument("--manifest", required=True)
    dialogue_turns.add_argument("--plan", required=True)
    dialogue_turns.add_argument("--output-dir", required=True)
    dialogue_turns.add_argument("--lead-in", type=float, default=0.35)
    dialogue_turns.add_argument("--asr-audit")
    dialogue_turns.add_argument("--result")
    eleven_speech = commands.add_parser(
        "generate-eleven-speech",
        help="generate one isolated ElevenLabs persona line with timestamp evidence",
    )
    eleven_speech.add_argument("--profile", default="cad_10")
    eleven_speech.add_argument("--voice-id", required=True)
    eleven_speech.add_argument("--text", required=True)
    eleven_speech.add_argument("--output", required=True)
    eleven_speech.add_argument("--model-id", default="eleven_v3")
    eleven_speech.add_argument("--seed", type=int, default=0)
    eleven_speech.add_argument("--live", action="store_true")
    eleven_speech.add_argument("--confirm-live", action="store_true")
    eleven_speech.add_argument("--result")
    eleven_ambience = commands.add_parser(
        "generate-eleven-ambience",
        help="generate one bounded ElevenLabs sound-effect or ambience stem",
    )
    eleven_ambience.add_argument("--profile", default="cad_10")
    eleven_ambience.add_argument("--text", required=True)
    eleven_ambience.add_argument("--seconds", type=float)
    eleven_ambience.add_argument("--loop", action="store_true")
    eleven_ambience.add_argument("--prompt-influence", type=float, default=0.3)
    eleven_ambience.add_argument("--output", required=True)
    eleven_ambience.add_argument("--model-id", default="eleven_text_to_sound_v2")
    eleven_ambience.add_argument("--live", action="store_true")
    eleven_ambience.add_argument("--confirm-live", action="store_true")
    eleven_ambience.add_argument("--result")
    eleven_background = commands.add_parser(
        "generate-eleven-background-dialogue",
        help="generate a bounded multi-voice background-dialogue stem",
    )
    eleven_background.add_argument("--profile", default="cad_10")
    eleven_background.add_argument("--inputs-json", required=True)
    eleven_background.add_argument("--output", required=True)
    eleven_background.add_argument("--seed", type=int, default=0)
    eleven_background.add_argument("--live", action="store_true")
    eleven_background.add_argument("--confirm-live", action="store_true")
    eleven_background.add_argument("--result")
    avatar = commands.add_parser("plan-avatar", help="generate one explicitly approved partner lip-sync clip")
    avatar.add_argument("--profile", default="cad_10")
    avatar.add_argument("--image", required=True)
    avatar.add_argument("--script", required=True)
    avatar.add_argument("--voice")
    avatar.add_argument("--series-manifest")
    avatar.add_argument("--character-id")
    avatar.add_argument("--gaze-direction", choices=["screen_left", "screen_right"], required=True)
    avatar.add_argument(
        "--speaker-position", choices=["only_person", "frame_left", "frame_right"],
        default="only_person",
        help="identify the sole speaker when the reference contains two people",
    )
    avatar.add_argument(
        "--response-anticipation", action="store_true",
        help="hold polite partner eyeline after a question while awaiting the answer",
    )
    avatar.add_argument("--performance", default="Restrained natural dramatic delivery, conversational pace.")
    avatar.add_argument("--seed", type=int, default=0)
    avatar.add_argument("--max-seconds", type=int, default=8)
    avatar.add_argument("--output-dir", default="outputs")
    avatar.add_argument("--allow-partner-avatar", action="store_true")
    avatar.add_argument("--live", action="store_true")
    avatar.add_argument("--confirm-live", action="store_true")
    avatar.add_argument("--result")
    assembly = commands.add_parser("assemble-proof", help="mux speech into a 6–10 second proof clip")
    assembly.add_argument("--video", required=True)
    assembly.add_argument("--audio", required=True)
    assembly.add_argument("--output", required=True)
    assembly.add_argument("--seconds", type=float, default=8.0)
    assembly.add_argument("--audio-delay", type=float, default=0.8)
    assembly.add_argument("--manifest")
    dialogue = commands.add_parser("assemble-dialogue", help="join two lip-synced speaker clips")
    dialogue.add_argument("--clip", action="append", required=True)
    dialogue.add_argument("--output", required=True)
    dialogue.add_argument("--seconds", type=float, default=8.0)
    dialogue.add_argument("--manifest")
    scene_assembly = commands.add_parser("assemble-scene", help="join a wide master and 3–5 lip-synced turns")
    scene_assembly.add_argument("--master", required=True)
    scene_assembly.add_argument("--clip", action="append", required=True)
    scene_assembly.add_argument("--master-seconds", type=float, default=3.0)
    scene_assembly.add_argument("--output", required=True)
    scene_assembly.add_argument("--seconds", type=float, default=15.0)
    scene_assembly.add_argument("--manifest")
    artifact_audit = commands.add_parser("audit-artifacts", help="classify a run's durable and recomputable files")
    artifact_audit.add_argument("run")
    artifact_audit.add_argument("--output")
    artifact_prune = commands.add_parser("prune-artifacts", help="remove only files classified as recomputable")
    artifact_prune.add_argument("run")
    artifact_prune.add_argument("--apply", action="store_true")
    artifact_prune.add_argument("--output")
    rejected_prune = commands.add_parser(
        "prune-rejected-media",
        help="delete only large failed/rejected media backed by retained review evidence",
    )
    rejected_prune.add_argument("run")
    rejected_prune.add_argument("--decisions", required=True)
    rejected_prune.add_argument("--minimum-mib", type=float, default=25.0)
    rejected_prune.add_argument("--apply", action="store_true")
    rejected_prune.add_argument("--output")
    prepare = commands.add_parser("prepare-dialogue", help="trim, pace, and reframe one synchronized turn")
    prepare.add_argument("--input", required=True)
    prepare.add_argument("--output", required=True)
    prepare.add_argument("--start", type=float, required=True)
    prepare.add_argument("--end", type=float, required=True)
    prepare.add_argument("--rate", type=float, default=1.0)
    prepare.add_argument("--crop", required=True, help="width:height:x:y")
    prepare.add_argument("--manifest")
    prepare_stage2 = commands.add_parser(
        "prepare-stage2-dialogue", help="trim native 16:9 dialogue without crop or padding")
    prepare_stage2.add_argument("--input", required=True)
    prepare_stage2.add_argument("--output", required=True)
    prepare_stage2.add_argument("--start", type=float, required=True)
    prepare_stage2.add_argument("--end", type=float, required=True)
    prepare_stage2.add_argument("--rate", type=float, default=1.0)
    prepare_stage2.add_argument("--manifest")
    prepare_stage2_square = commands.add_parser(
        "prepare-stage2-square-dialogue",
        help="convert one approved square avatar performance to a safe native-16:9 dialogue clip",
    )
    prepare_stage2_square.add_argument("--input", required=True)
    prepare_stage2_square.add_argument("--reference-origin", required=True)
    prepare_stage2_square.add_argument("--output", required=True)
    prepare_stage2_square.add_argument("--start", type=float, required=True)
    prepare_stage2_square.add_argument("--end", type=float, required=True)
    prepare_stage2_square.add_argument("--rate", type=float, default=1.0)
    prepare_stage2_square.add_argument("--crop", required=True, help="width:height:x:y")
    prepare_stage2_square.add_argument("--manifest")
    room_tone = commands.add_parser("generate-room-tone", help="create deterministic non-verbal ambience")
    room_tone.add_argument("--output", required=True)
    room_tone.add_argument("--seconds", type=float, required=True)
    room_tone.add_argument("--transient", action="append", type=float, default=[])
    clinic_ambience = commands.add_parser(
        "generate-clinic-ambience", help="create an audible Stage 2 clinic ambience bed")
    clinic_ambience.add_argument("--output", required=True)
    clinic_ambience.add_argument("--seconds", type=float, required=True)
    clinic_ambience.add_argument("--fade-seconds", type=float, default=0.5)
    timeline = commands.add_parser("assemble-timeline", help="assemble a reusable provenance timeline")
    timeline.add_argument("--timeline", required=True)
    timeline.add_argument("--output", required=True)
    timeline.add_argument("--ambience")
    timeline.add_argument("--manifest")
    stage2_timeline = commands.add_parser(
        "assemble-stage2", help="assemble a native-16:9 typed Stage 2 timeline")
    stage2_timeline.add_argument("--timeline", required=True)
    stage2_timeline.add_argument("--output", required=True)
    stage2_timeline.add_argument("--ambience")
    stage2_timeline.add_argument("--manifest")
    av_sync = commands.add_parser(
        "audit-av-sync",
        help="evaluate timestamped AV-offset evidence and the normal-speed review gate",
    )
    av_sync.add_argument("evidence")
    av_sync.add_argument("--output")
    return result


def emit_json(packet: dict, destination: str | None = None) -> None:
    rendered = json.dumps(packet, indent=2, sort_keys=True) + "\n"
    if destination:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


def avatar_image_input(value: str | Path, *, live: bool = False) -> str:
    if str(value).startswith("https://"):
        return str(value)
    if live:
        raise VideoGenError(
            "live partner-avatar generation requires a public HTTPS image URL; "
            "local/data images are rejected before reservation"
        )
    source = Path(value)
    media_type = mimetypes.guess_type(source.name)[0]
    if media_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise VideoGenError("avatar image must be JPEG, PNG, or WebP")
    return f"data:{media_type};base64,{base64.b64encode(source.read_bytes()).decode()}"


def image_video_input(
    value: str | Path,
    *,
    live: bool = False,
    allow_live_inline: bool = False,
) -> str:
    if str(value).startswith("https://"):
        return str(value)
    if live and not allow_live_inline:
        raise VideoGenError(
            "live partner-I2V generation requires a public HTTPS image URL; "
            "use --inline-local-assets to send a bounded local image directly to the provider"
        )
    source = Path(value)
    if not source.is_file():
        raise VideoGenError("I2V image does not exist")
    if source.stat().st_size > 5 * 1024 * 1024:
        raise VideoGenError("inline I2V image exceeds the 5 MiB safety limit")
    media_type = mimetypes.guess_type(source.name)[0]
    if media_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise VideoGenError("I2V image must be JPEG, PNG, or WebP")
    return f"data:{media_type};base64,{base64.b64encode(source.read_bytes()).decode()}"


def image_video_audio_input(
    value: str | Path,
    *,
    live: bool = False,
    allow_live_inline: bool = False,
) -> str:
    if str(value).startswith("https://"):
        return str(value)
    if live and not allow_live_inline:
        raise VideoGenError(
            "live partner-I2V generation requires a public HTTPS audio URL; "
            "use --inline-local-assets to send bounded local audio directly to the provider"
        )
    source = Path(value)
    if not source.is_file():
        raise VideoGenError("I2V audio does not exist")
    if source.stat().st_size > 5 * 1024 * 1024:
        raise VideoGenError("inline I2V audio exceeds the 5 MiB safety limit")
    media_type = mimetypes.guess_type(source.name)[0]
    if media_type not in {"audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp4", "audio/aac"}:
        raise VideoGenError("I2V audio must be WAV, MP3, MP4 audio, or AAC")
    return f"data:{media_type};base64,{base64.b64encode(source.read_bytes()).decode()}"


def cosmos_image_input(value: str | Path) -> str:
    """Cosmos explicitly accepts inline image Data URLs, including for live calls."""
    if str(value).startswith("https://"):
        return str(value)
    source = Path(value)
    media_type = mimetypes.guess_type(source.name)[0]
    if media_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise VideoGenError("Cosmos image must be JPEG, PNG, or WebP")
    return f"data:{media_type};base64,{base64.b64encode(source.read_bytes()).decode()}"


def canonical_voice_binding(
    series_manifest: str | None, character_id: str | None,
) -> tuple[str, dict] | None:
    if series_manifest is None and character_id is None:
        return None
    if not series_manifest or not character_id:
        raise VideoGenError("voice binding requires --series-manifest and --character-id together")
    series = load_series(series_manifest)
    persona = next(
        (item for item in series["canonical_personas"] if item["character_id"] == character_id),
        None,
    )
    if persona is None:
        raise VideoGenError(f"unknown canonical character: {character_id}")
    realization = persona["voice"].get("voice_realization")
    if realization is None:
        raise VideoGenError(
            f"canonical character {character_id} uses the Stage 3 voice-plan contract; "
            "use the voice-plan commands instead of a Stage 2 request binding"
        )
    return persona["voice"]["provider_voice"], realization


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        config = ProjectConfig.load(args.config)
        if args.command == "preflight":
            cap = config.profile_cap(args.profile)
            emit_json({"ok": True, "profile": args.profile, "cap_usd": str(cap),
                       "explicit_run_cap_usd": (str(args.run_cap_usd)
                                                if args.run_cap_usd is not None else None),
                       "mode": "dry_run", "approved_models": len(config.raw["approved_models"])},
                      args.output)
            return 0
        if args.command == "audit-av-sync":
            report = audit_av_sync_file(args.evidence)
            emit_json(report, args.output)
            if report["evidence_kind"] == "calibration_fixture":
                return 0 if report["objective_gate"] == "pass" else 2
            return 0 if report["acceptance_gate"] == "pass" else 2
        if args.command == "validate-scene":
            scene = load_scene(args.scene)
            spatial_audit = audit_scene(scene)
            if spatial_audit["gate"] != "pass":
                raise VideoGenError(
                    f"scene spatial audit blocked generation with {spatial_audit['blocking_findings']} finding(s)"
                )
            prompts = {shot["id"]: compile_prompt(scene, shot["id"]) for shot in scene["shots"]}
            emit_json({"ok": True, "scene": scene["id"], "prompts": prompts,
                       "spatial_audit": spatial_audit}, args.output)
            return 0
        if args.command == "validate-production":
            production = load_production(args.production)
            emit_json({"ok": True, "production": production["id"],
                       "ordered_scene_ids": [item["id"] for item in production["scenes"]],
                       "independently_resumable": True})
            return 0
        if args.command == "validate-stage2":
            sequence = load_stage2_sequence(args.sequence)
            prompts = {
                shot["shot_id"]: compile_stage2_prompt(sequence, shot["shot_id"])
                for scene in sequence["scenes"] for shot in scene["planned_shots"]
            }
            source_take_prompts = {
                take["take_id"]: compile_stage2_take_prompt(sequence, take["take_id"])
                for take in sequence["planned_source_takes"]
            }
            authorization_prompts = {**prompts, **source_take_prompts}
            spatial_audit = {
                "schema_version": "2.0",
                "audit_type": "storyboard_spatial",
                "audit_stage": "storyboard",
                "hierarchy": sequence["hierarchy"],
                "prompt_sha256s": {
                    prompt_id: text_sha256(prompt)
                    for prompt_id, prompt in authorization_prompts.items()
                },
                "blocking_findings": 0,
                "gate": "pass",
                "evidence": (
                    "Stage 2 schema, hierarchy, series persona inheritance, reference anchors, "
                    "typed setups, native 16:9 declarations, face-safe dialogue composition, "
                    "essential action states, sound plan and edit policy validated."
                ),
            }
            emit_json({
                "ok": True,
                "hierarchy": sequence["hierarchy"],
                "canonical_persona_versions": {
                    item["character_id"]: item["persona_version"]
                    for item in sequence["_series"]["canonical_personas"]
                },
                "prompts": prompts,
                "source_take_prompts": source_take_prompts,
                "spatial_audit": spatial_audit,
            }, args.output)
            return 0
        if args.command == "validate-voice-plan":
            voice_plan = load_voice_plan(args.plan)
            emit_json({
                "ok": True,
                "sequence_id": voice_plan["sequence_id"],
                "readiness": voice_readiness_report(voice_plan),
                "budget": voice_budget_report(voice_plan, config),
            }, args.output)
            return 0
        if args.command == "match-voices":
            voice_plan = load_voice_plan(args.plan)
            persona = voice_plan["_personas"].get(args.character)
            if persona is None:
                raise VideoGenError(f"character is not bound in plan: {args.character}")
            if args.catalog:
                catalog_packet = json.loads(
                    Path(args.catalog).read_text(encoding="utf-8")
                )
                voices = (
                    catalog_packet.get("voices")
                    if isinstance(catalog_packet, dict) else catalog_packet
                )
                if not isinstance(voices, list):
                    raise VideoGenError("voice catalog must be a list or contain voices")
                catalog_source = "cached"
            else:
                voices = ElevenLabsClient(
                    os.environ.get("ELEVENLABS_KEY", "")
                ).list_voices()
                catalog_source = "elevenlabs_live_read_only"
            emit_json({
                "schema_version": "1.0",
                "audit_type": "dynamic_voice_shortlist",
                "character_id": args.character,
                "voice_persona_id": persona["voice"]["voice_persona_id"],
                "catalog_source": catalog_source,
                "automatic_casting_allowed": False,
                "protected_attributes_used": False,
                "candidates": rank_voice_catalog(persona, voices, limit=args.top),
            }, args.output)
            return 0
        if args.command == "audit-stage2":
            sequence = load_stage2_sequence(args.sequence)
            timeline_packet = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
            observations = (json.loads(Path(args.observations).read_text(encoding="utf-8"))
                            if args.observations else None)
            report = audit_stage2_sequence(
                sequence, timeline_packet, final_media=args.final, observations=observations,
                allowed_generation_models=config.cinematic_generation_model_ids(),
            )
            emit_json(report, args.output)
            return 0 if report["promotion_allowed"] else 2
        if args.command == "audit-scene":
            report = audit_scene(load_scene(args.scene))
            emit_json(report, args.output)
            return 0 if report["gate"] == "pass" else 2
        if args.command == "audit-draft":
            scene = load_scene(args.scene)
            sheet = args.contact_sheet or f"{args.video}.contact-sheet.png"
            contact_sheet(args.video, sheet)
            observations = (json.loads(Path(args.observations).read_text(encoding="utf-8"))
                            if args.observations else None)
            report = audit_draft(scene, args.shot, args.video, observations, sheet)
            emit_json(report, args.output)
            return 0 if report["promotion_allowed"] else 2
        if args.command == "audit-stage":
            scene = load_scene(args.scene)
            observations = json.loads(Path(args.observations).read_text(encoding="utf-8"))
            if args.stage in {"cheap_draft", "final_candidate"}:
                if not args.video or not args.shot:
                    raise VideoGenError("media audit stages require --video and --shot")
                sheet = args.contact_sheet or f"{args.video}.contact-sheet.png"
                contact_sheet(args.video, sheet)
                function = audit_draft if args.stage == "cheap_draft" else audit_final_candidate
                report = function(scene, args.shot, args.video, observations, sheet)
            else:
                report = audit_continuity(scene, observations, stage=args.stage)
            emit_json(report, args.output)
            return 0 if report["promotion_allowed"] else 2
        if args.command == "audit-artifacts":
            report = audit_run_artifacts(args.run)
            emit_json(report, args.output)
            return 0
        if args.command == "prune-artifacts":
            report = prune_recomputable_artifacts(args.run, apply=args.apply)
            emit_json(report, args.output)
            return 0
        if args.command == "prune-rejected-media":
            if args.minimum_mib < 0:
                raise VideoGenError("--minimum-mib cannot be negative")
            report = prune_rejected_media(
                args.run,
                args.decisions,
                minimum_bytes=int(args.minimum_mib * 1024 * 1024),
                apply=args.apply,
            )
            emit_json(report, args.output)
            return 0
        if args.command == "assemble-proof":
            report = assemble_with_audio(args.video, args.audio, args.output,
                                         target_seconds=args.seconds,
                                         audio_delay_seconds=args.audio_delay)
            emit_json(report, args.manifest)
            return 0
        if args.command == "prepare-dialogue":
            try:
                crop = tuple(int(value) for value in args.crop.split(":"))
                if len(crop) != 4:
                    raise ValueError
            except ValueError as exc:
                raise VideoGenError("--crop must be width:height:x:y") from exc
            report = prepare_dialogue_clip(
                args.input, args.output, start=args.start, end=args.end,
                rate=args.rate, crop=crop,
            )
            emit_json(report, args.manifest)
            return 0
        if args.command == "prepare-stage2-dialogue":
            report = prepare_stage2_dialogue_clip(
                args.input, args.output, start=args.start, end=args.end, rate=args.rate,
            )
            emit_json(report, args.manifest)
            return 0
        if args.command == "prepare-stage2-square-dialogue":
            try:
                crop = tuple(int(item) for item in args.crop.split(":"))
                if len(crop) != 4:
                    raise ValueError
            except ValueError as exc:
                raise VideoGenError("--crop must be width:height:x:y") from exc
            report = prepare_stage2_square_dialogue_clip(
                args.input, args.output, reference_origin=args.reference_origin,
                start=args.start, end=args.end, rate=args.rate, crop=crop,
            )
            emit_json(report, args.manifest)
            return 0
        if args.command == "assemble-dialogue":
            report = assemble_lipsynced_dialogue(args.clip, args.output,
                                                 target_seconds=args.seconds)
            emit_json(report, args.manifest)
            return 0
        if args.command == "assemble-scene":
            report = assemble_master_dialogue_scene(
                args.master, args.clip, args.output, target_seconds=args.seconds,
                master_seconds=args.master_seconds,
            )
            emit_json(report, args.manifest)
            return 0
        if args.command == "generate-room-tone":
            report = generate_room_tone(args.output, duration=args.seconds,
                                        transient_times=args.transient)
            emit_json(report)
            return 0
        if args.command == "generate-clinic-ambience":
            report = generate_clinic_ambience(
                args.output, duration=args.seconds, fade_seconds=args.fade_seconds,
            )
            emit_json(report)
            return 0
        if args.command == "assemble-timeline":
            timeline_packet = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
            report = assemble_timeline(
                timeline_packet["intervals"], args.output,
                ambience=args.ambience or timeline_packet.get("ambience"),
                target_seconds=timeline_packet.get("target_seconds"),
            )
            emit_json(report, args.manifest)
            return 0
        if args.command == "assemble-stage2":
            timeline_packet = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
            ambience = args.ambience or timeline_packet.get("ambience")
            if not ambience:
                raise VideoGenError("Stage 2 assembly requires an ambience bed")
            report = assemble_stage2_timeline(
                timeline_packet["intervals"], args.output, ambience=ambience,
                target_seconds=float(timeline_packet["target_seconds"]),
                fade_seconds=float(timeline_packet.get("fade_seconds", 0.5)),
                ambience_volume=float(timeline_packet.get("ambience_volume", 1.0)),
            )
            emit_json(report, args.manifest)
            return 0
        ledger = Ledger(args.ledger)
        orchestrator = Orchestrator(
            config, ledger, args.profile, run_cap_usd=args.run_cap_usd,
            partner_avatar_attempt_cap=args.partner_avatar_attempt_cap,
        )
        if args.command == "plan-speech":
            voice_binding = canonical_voice_binding(args.series_manifest, args.character_id)
            request = orchestrator.run_speech(
                args.text, seed=args.seed, live=args.live, confirmed=args.confirm_live,
                voice_realization=(voice_binding[1] if voice_binding else None),
            )
            emit_json({**request.__dict__, "reserved_usd": str(request.reserved_usd)}, args.result)
            return 0
        if args.command == "plan-voice-audition":
            voice_plan = load_voice_plan(args.plan)
            spec = voice_audition_spec(voice_plan, args.character)
            request = orchestrator.run_voice_audition(
                spec, live=args.live, confirmed=args.confirm_live,
                output_dir=args.output_dir,
            )
            emit_json(
                {**request.__dict__, "reserved_usd": str(request.reserved_usd)},
                args.result,
            )
            return 0
        if args.command == "plan-dialogue-candidate":
            voice_plan = load_voice_plan(args.plan)
            spec = dialogue_candidate_spec(voice_plan)
            request = orchestrator.run_dialogue_candidate(
                spec,
                live=args.live,
                confirmed=args.confirm_live,
                output_dir=args.output_dir,
            )
            emit_json(
                {**request.__dict__, "reserved_usd": str(request.reserved_usd)},
                args.result,
            )
            return 0
        if args.command == "prepare-dialogue-turns":
            report = prepare_dialogue_turns(
                args.audio,
                args.manifest,
                args.plan,
                args.output_dir,
                lead_in_seconds=args.lead_in,
                asr_audit=args.asr_audit,
            )
            emit_json(report, args.result)
            return 0
        if args.command == "generate-eleven-speech":
            spec = {
                "provider": "elevenlabs",
                "operation": "timestamped_single_speaker_line",
                "model_id": args.model_id,
                "voice_id": args.voice_id,
                "text": args.text,
                "seed": args.seed,
                "output_format": "wav_24000",
                "live": bool(args.live),
            }
            if not args.live:
                emit_json(spec, args.result)
                return 0
            if not args.confirm_live:
                raise VideoGenError("live ElevenLabs speech requires --confirm-live")
            generated = ElevenLabsClient(
                os.environ.get("ELEVENLABS_KEY", "")
            ).text_to_speech(
                args.text,
                args.voice_id,
                model_id=args.model_id,
                seed=args.seed,
            )
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(generated.audio)
            emit_json({
                **spec,
                "provider_request_id": generated.provider_request_id,
                "character_cost": generated.character_cost,
                "output": str(output),
                "sha256": hashlib.sha256(generated.audio).hexdigest(),
                "bytes": len(generated.audio),
                "alignment": generated.alignment,
                "normalized_alignment": generated.normalized_alignment,
            }, args.result)
            return 0
        if args.command == "generate-eleven-ambience":
            spec = {
                "provider": "elevenlabs",
                "operation": "text_to_sound_effect",
                "model_id": args.model_id,
                "text": args.text,
                "duration_seconds": args.seconds,
                "loop": bool(args.loop),
                "prompt_influence": args.prompt_influence,
                "output_format": "mp3_44100_192",
                "live": bool(args.live),
            }
            if not args.live:
                emit_json(spec, args.result)
                return 0
            if not args.confirm_live:
                raise VideoGenError("live ElevenLabs ambience requires --confirm-live")
            generated = ElevenLabsClient(
                os.environ.get("ELEVENLABS_KEY", "")
            ).sound_effect(
                args.text,
                duration_seconds=args.seconds,
                loop=args.loop,
                prompt_influence=args.prompt_influence,
                model_id=args.model_id,
            )
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(generated.audio)
            emit_json({
                **spec,
                "provider_request_id": generated.provider_request_id,
                "character_cost": generated.character_cost,
                "content_type": generated.content_type,
                "output": str(output),
                "sha256": hashlib.sha256(generated.audio).hexdigest(),
                "bytes": len(generated.audio),
            }, args.result)
            return 0
        if args.command == "generate-eleven-background-dialogue":
            packet = json.loads(Path(args.inputs_json).read_text(encoding="utf-8"))
            inputs = packet.get("inputs") if isinstance(packet, dict) else packet
            if not isinstance(inputs, list) or not 2 <= len(inputs) <= 10:
                raise VideoGenError("background dialogue requires 2 to 10 inputs")
            normalized_inputs = []
            for item in inputs:
                if not isinstance(item, dict):
                    raise VideoGenError("background dialogue inputs must be objects")
                text_value = str(item.get("text", "")).strip()
                voice_id = str(item.get("voice_id", "")).strip()
                if not text_value or not voice_id:
                    raise VideoGenError(
                        "background dialogue inputs require text and voice_id"
                    )
                normalized_inputs.append({"text": text_value, "voice_id": voice_id})
            spec = {
                "provider": "elevenlabs",
                "operation": "multi_voice_background_dialogue",
                "model_id": "eleven_v3",
                "inputs": normalized_inputs,
                "seed": args.seed,
                "output_format": "wav_24000",
                "live": bool(args.live),
            }
            if not args.live:
                emit_json(spec, args.result)
                return 0
            if not args.confirm_live:
                raise VideoGenError(
                    "live ElevenLabs background dialogue requires --confirm-live"
                )
            generated = ElevenLabsClient(
                os.environ.get("ELEVENLABS_KEY", "")
            ).text_to_dialogue(normalized_inputs, seed=args.seed)
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(generated.audio)
            emit_json({
                **spec,
                "provider_request_id": generated.provider_request_id,
                "character_cost": generated.character_cost,
                "output": str(output),
                "sha256": hashlib.sha256(generated.audio).hexdigest(),
                "bytes": len(generated.audio),
                "voice_segments": generated.voice_segments,
                "alignment": generated.alignment,
                "normalized_alignment": generated.normalized_alignment,
            }, args.result)
            return 0
        if args.command == "plan-avatar":
            voice_binding = canonical_voice_binding(args.series_manifest, args.character_id)
            voice = args.voice or (voice_binding[0] if voice_binding else None)
            if not voice:
                raise VideoGenError(
                    "avatar generation requires --voice or a canonical series voice binding"
                )
            request = orchestrator.run_avatar(
                avatar_image_input(args.image, live=args.live), args.script, voice,
                seed=args.seed,
                max_seconds=args.max_seconds, gaze_direction=args.gaze_direction,
                speaker_position=args.speaker_position,
                response_anticipation=args.response_anticipation,
                performance_direction=args.performance, live=args.live, confirmed=args.confirm_live,
                allow_partner=args.allow_partner_avatar,
                voice_realization=(voice_binding[1] if voice_binding else None),
                output_dir=args.output_dir)
            emit_json({**request.__dict__, "reserved_usd": str(request.reserved_usd)}, args.result)
            return 0
        if args.command == "plan-image-video":
            prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip()
            if args.live:
                if not args.scene_audit or not args.take_id or not args.repair_authorization:
                    raise VideoGenError(
                        "live I2V requires --scene-audit, --take-id, and --repair-authorization"
                    )
                try:
                    scene_packet = json.loads(Path(args.scene_audit).read_text(encoding="utf-8"))
                    verify_storyboard_authorization(scene_packet, args.take_id, prompt)
                    repair_packet = json.loads(
                        Path(args.repair_authorization).read_text(encoding="utf-8")
                    )
                    verify_bounded_repair_authorization(repair_packet, prompt)
                except (OSError, json.JSONDecodeError, ValueError) as exc:
                    raise VideoGenError(str(exc)) from exc
            request = orchestrator.run_image_video(
                image_video_input(
                    args.image, live=args.live,
                    allow_live_inline=args.inline_local_assets,
                ), prompt,
                audio_input=(image_video_audio_input(
                    args.audio, live=args.live,
                    allow_live_inline=args.inline_local_assets,
                )
                             if args.audio else None),
                seconds=args.seconds, seed=args.seed,
                live=args.live, confirmed=args.confirm_live,
                allow_partner=args.allow_partner_i2v, output_dir=args.output_dir,
                webhook_url=args.webhook_url,
                webhook_result_path=args.webhook_result,
                webhook_wait_seconds=args.webhook_wait_seconds,
            )
            emit_json({**request.__dict__, "reserved_usd": str(request.reserved_usd)}, args.result)
            return 0
        if args.prompt_file:
            prompt = Path(args.prompt_file).read_text(encoding="utf-8").strip()
        elif args.scene_manifest:
            if not args.shot_id:
                raise VideoGenError("--scene-manifest requires --shot-id")
            prompt = compile_prompt(load_scene(args.scene_manifest), args.shot_id)
        else:
            prompt = args.prompt
        if args.live:
            if not args.scene_audit or not args.shot_id:
                raise VideoGenError("live video requires --scene-audit and --shot-id")
            try:
                scene_packet = json.loads(Path(args.scene_audit).read_text(encoding="utf-8"))
                verify_storyboard_authorization(scene_packet, args.shot_id, prompt)
                if args.role in {"final_video", "cosmos_world_video"}:
                    if args.draft_audit:
                        draft_packet = json.loads(Path(args.draft_audit).read_text(encoding="utf-8"))
                        verify_promotion_authorization(draft_packet, prompt)
                    elif args.repair_authorization:
                        repair_packet = json.loads(Path(args.repair_authorization).read_text(encoding="utf-8"))
                        verify_bounded_repair_authorization(repair_packet, prompt)
                    else:
                        raise ValueError(
                            "promoted live video requires --draft-audit or --repair-authorization")
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                raise VideoGenError(str(exc)) from exc
        request = orchestrator.run_video(
            args.role, prompt, seed=args.seed,
            image_input=(cosmos_image_input(args.image) if args.image else None),
            live=args.live, confirmed=args.confirm_live,
            output_dir=args.output_dir,
            webhook_url=args.webhook_url,
            webhook_result_path=args.webhook_result,
            webhook_wait_seconds=args.webhook_wait_seconds)
        emit_json({**request.__dict__, "reserved_usd": str(request.reserved_usd)}, args.result)
        return 0
    except VideoGenError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
