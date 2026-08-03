from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
from decimal import Decimal
from pathlib import Path

from .auditor import (audit_continuity, audit_draft, audit_final_candidate, audit_scene,
                      verify_bounded_repair_authorization, verify_promotion_authorization,
                      verify_storyboard_authorization)
from .config import ProjectConfig
from .errors import VideoGenError
from .ledger import Ledger
from .media import (assemble_lipsynced_dialogue, assemble_master_dialogue_scene,
                    assemble_timeline, assemble_with_audio, contact_sheet,
                    generate_room_tone, prepare_dialogue_clip)
from .orchestrator import Orchestrator
from .production import compile_prompt, load_production, load_scene
from .retention import audit_run_artifacts, prune_recomputable_artifacts


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
    plan.add_argument("--role", choices=["draft_video", "final_video"], required=True)
    prompt_source = plan.add_mutually_exclusive_group(required=True)
    prompt_source.add_argument("--prompt")
    prompt_source.add_argument("--prompt-file")
    prompt_source.add_argument("--scene-manifest")
    plan.add_argument("--seed", type=int, default=0)
    plan.add_argument("--live", action="store_true")
    plan.add_argument("--confirm-live", action="store_true")
    plan.add_argument("--scene-audit")
    plan.add_argument("--shot-id")
    plan.add_argument("--draft-audit")
    plan.add_argument("--repair-authorization")
    plan.add_argument("--result")
    plan.add_argument("--output-dir", default="outputs")
    speech = commands.add_parser("plan-speech", help="reserve or generate one bounded speech line")
    speech.add_argument("--profile", default="cad_10")
    speech.add_argument("--text", required=True)
    speech.add_argument("--seed", type=int, default=0)
    speech.add_argument("--live", action="store_true")
    speech.add_argument("--confirm-live", action="store_true")
    speech.add_argument("--result")
    avatar = commands.add_parser("plan-avatar", help="generate one explicitly approved partner lip-sync clip")
    avatar.add_argument("--profile", default="cad_10")
    avatar.add_argument("--image", required=True)
    avatar.add_argument("--script", required=True)
    avatar.add_argument("--voice", required=True)
    avatar.add_argument("--gaze-direction", choices=["screen_left", "screen_right"], required=True)
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
    prepare = commands.add_parser("prepare-dialogue", help="trim, pace, and reframe one synchronized turn")
    prepare.add_argument("--input", required=True)
    prepare.add_argument("--output", required=True)
    prepare.add_argument("--start", type=float, required=True)
    prepare.add_argument("--end", type=float, required=True)
    prepare.add_argument("--rate", type=float, default=1.0)
    prepare.add_argument("--crop", required=True, help="width:height:x:y")
    prepare.add_argument("--manifest")
    room_tone = commands.add_parser("generate-room-tone", help="create deterministic non-verbal ambience")
    room_tone.add_argument("--output", required=True)
    room_tone.add_argument("--seconds", type=float, required=True)
    room_tone.add_argument("--transient", action="append", type=float, default=[])
    timeline = commands.add_parser("assemble-timeline", help="assemble a reusable provenance timeline")
    timeline.add_argument("--timeline", required=True)
    timeline.add_argument("--output", required=True)
    timeline.add_argument("--ambience")
    timeline.add_argument("--manifest")
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
        if args.command == "assemble-timeline":
            timeline_packet = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
            report = assemble_timeline(
                timeline_packet["intervals"], args.output,
                ambience=args.ambience or timeline_packet.get("ambience"),
                target_seconds=timeline_packet.get("target_seconds"),
            )
            emit_json(report, args.manifest)
            return 0
        ledger = Ledger(args.ledger)
        orchestrator = Orchestrator(
            config, ledger, args.profile, run_cap_usd=args.run_cap_usd,
            partner_avatar_attempt_cap=args.partner_avatar_attempt_cap,
        )
        if args.command == "plan-speech":
            request = orchestrator.run_speech(
                args.text, seed=args.seed, live=args.live, confirmed=args.confirm_live)
            emit_json({**request.__dict__, "reserved_usd": str(request.reserved_usd)}, args.result)
            return 0
        if args.command == "plan-avatar":
            request = orchestrator.run_avatar(
                avatar_image_input(args.image, live=args.live), args.script, args.voice,
                seed=args.seed,
                max_seconds=args.max_seconds, gaze_direction=args.gaze_direction,
                performance_direction=args.performance, live=args.live, confirmed=args.confirm_live,
                allow_partner=args.allow_partner_avatar, output_dir=args.output_dir)
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
                if args.role == "final_video":
                    if args.draft_audit:
                        draft_packet = json.loads(Path(args.draft_audit).read_text(encoding="utf-8"))
                        verify_promotion_authorization(draft_packet, prompt)
                    elif args.repair_authorization:
                        repair_packet = json.loads(Path(args.repair_authorization).read_text(encoding="utf-8"))
                        verify_bounded_repair_authorization(repair_packet, prompt)
                    else:
                        raise ValueError(
                            "final live video requires --draft-audit or --repair-authorization")
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                raise VideoGenError(str(exc)) from exc
        request = orchestrator.run_video(
            args.role, prompt, seed=args.seed, live=args.live, confirmed=args.confirm_live,
            output_dir=args.output_dir)
        emit_json({**request.__dict__, "reserved_usd": str(request.reserved_usd)}, args.result)
        return 0
    except VideoGenError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
