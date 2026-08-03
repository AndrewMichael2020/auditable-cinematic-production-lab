from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
from pathlib import Path

from .auditor import (audit_draft, audit_scene, verify_promotion_authorization,
                      verify_storyboard_authorization)
from .config import ProjectConfig
from .errors import VideoGenError
from .ledger import Ledger
from .media import (assemble_lipsynced_dialogue, assemble_master_dialogue_scene,
                    assemble_with_audio, contact_sheet, prepare_dialogue_clip)
from .orchestrator import Orchestrator
from .production import compile_prompt, load_scene
from .retention import audit_run_artifacts, prune_recomputable_artifacts


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="video-gen")
    result.add_argument("--config", default="project.json")
    result.add_argument("--ledger", default="runs/ledger.sqlite3")
    commands = result.add_subparsers(dest="command", required=True)
    preflight = commands.add_parser("preflight", help="validate configuration without spending")
    preflight.add_argument("--profile", default="cad_10")
    validate = commands.add_parser("validate-scene", help="validate and compile the golden scene")
    validate.add_argument("scene", nargs="?", default="scenes/golden-scene.json")
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
    plan = commands.add_parser("plan-video", help="reserve and print a dry-run video request")
    plan.add_argument("--profile", default="cad_10")
    plan.add_argument("--role", choices=["draft_video", "final_video"], required=True)
    plan.add_argument("--prompt", required=True)
    plan.add_argument("--seed", type=int, default=0)
    plan.add_argument("--live", action="store_true")
    plan.add_argument("--confirm-live", action="store_true")
    plan.add_argument("--scene-audit")
    plan.add_argument("--shot-id")
    plan.add_argument("--draft-audit")
    speech = commands.add_parser("plan-speech", help="reserve or generate one bounded speech line")
    speech.add_argument("--profile", default="cad_10")
    speech.add_argument("--text", required=True)
    speech.add_argument("--seed", type=int, default=0)
    speech.add_argument("--live", action="store_true")
    speech.add_argument("--confirm-live", action="store_true")
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
    return result


def emit_json(packet: dict, destination: str | None = None) -> None:
    rendered = json.dumps(packet, indent=2, sort_keys=True) + "\n"
    if destination:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


def avatar_image_input(value: str | Path) -> str:
    if str(value).startswith("https://"):
        return str(value)
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
            print(json.dumps({"ok": True, "profile": args.profile, "cap_usd": str(cap),
                              "mode": "dry_run", "approved_models": len(config.raw["approved_models"])}, indent=2))
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
                       "spatial_audit": spatial_audit})
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
        ledger = Ledger(args.ledger)
        if args.command == "plan-speech":
            request = Orchestrator(config, ledger, args.profile).run_speech(
                args.text, seed=args.seed, live=args.live, confirmed=args.confirm_live)
            print(json.dumps({**request.__dict__, "reserved_usd": str(request.reserved_usd)}, indent=2))
            return 0
        if args.command == "plan-avatar":
            request = Orchestrator(config, ledger, args.profile).run_avatar(
                avatar_image_input(args.image), args.script, args.voice, seed=args.seed,
                max_seconds=args.max_seconds, gaze_direction=args.gaze_direction,
                performance_direction=args.performance, live=args.live, confirmed=args.confirm_live,
                allow_partner=args.allow_partner_avatar, output_dir=args.output_dir)
            print(json.dumps({**request.__dict__, "reserved_usd": str(request.reserved_usd)}, indent=2))
            return 0
        if args.live:
            if not args.scene_audit or not args.shot_id:
                raise VideoGenError("live video requires --scene-audit and --shot-id")
            try:
                scene_packet = json.loads(Path(args.scene_audit).read_text(encoding="utf-8"))
                verify_storyboard_authorization(scene_packet, args.shot_id, args.prompt)
                if args.role == "final_video":
                    if not args.draft_audit:
                        raise ValueError("final live video requires --draft-audit")
                    draft_packet = json.loads(Path(args.draft_audit).read_text(encoding="utf-8"))
                    verify_promotion_authorization(draft_packet, args.prompt)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                raise VideoGenError(str(exc)) from exc
        request = Orchestrator(config, ledger, args.profile).run_video(
            args.role, args.prompt, seed=args.seed, live=args.live, confirmed=args.confirm_live)
        print(json.dumps({**request.__dict__, "reserved_usd": str(request.reserved_usd)}, indent=2))
        return 0
    except VideoGenError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
