from __future__ import annotations

import argparse
import json
import sys
from .config import ProjectConfig
from .errors import VideoGenError
from .ledger import Ledger
from .orchestrator import Orchestrator
from .production import compile_prompt, load_scene


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="video-gen")
    result.add_argument("--config", default="project.json")
    result.add_argument("--ledger", default="runs/ledger.sqlite3")
    commands = result.add_subparsers(dest="command", required=True)
    preflight = commands.add_parser("preflight", help="validate configuration without spending")
    preflight.add_argument("--profile", default="cad_10")
    validate = commands.add_parser("validate-scene", help="validate and compile the golden scene")
    validate.add_argument("scene", nargs="?", default="scenes/golden-scene.json")
    plan = commands.add_parser("plan-video", help="reserve and print a dry-run video request")
    plan.add_argument("--profile", default="cad_10")
    plan.add_argument("--role", choices=["draft_video", "final_video"], required=True)
    plan.add_argument("--prompt", required=True)
    plan.add_argument("--seed", type=int, default=0)
    plan.add_argument("--live", action="store_true")
    plan.add_argument("--confirm-live", action="store_true")
    return result


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
            prompts = {shot["id"]: compile_prompt(scene, shot["id"]) for shot in scene["shots"]}
            print(json.dumps({"ok": True, "scene": scene["id"], "prompts": prompts}, indent=2))
            return 0
        ledger = Ledger(args.ledger)
        request = Orchestrator(config, ledger, args.profile).run_video(
            args.role, args.prompt, seed=args.seed, live=args.live, confirmed=args.confirm_live)
        print(json.dumps({**request.__dict__, "reserved_usd": str(request.reserved_usd)}, indent=2))
        return 0
    except VideoGenError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
