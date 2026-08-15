from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable

from .errors import PolicyError


RUN_MEDIA_SUFFIXES = {
    ".aac", ".avi", ".flac", ".gif", ".gz", ".jpeg", ".jpg", ".m4a",
    ".mkv", ".mov", ".mp3", ".mp4", ".png", ".tar", ".wav", ".webm",
    ".webp", ".zip",
}


def load_policy(path: str | Path) -> dict[str, Any]:
    try:
        policy = json.loads(Path(path).read_text(encoding="utf-8"))
        threshold = int(policy["threshold_bytes"])
        legacy = policy["legacy_large_files"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise PolicyError(f"invalid artifact policy: {exc}") from exc
    if threshold <= 0 or not isinstance(legacy, dict):
        raise PolicyError("artifact policy requires a positive threshold and legacy map")
    return policy


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True
    )
    return [root / item.decode() for item in result.stdout.split(b"\0") if item]


def changed_files(root: Path, base_ref: str | None) -> set[str]:
    if not base_ref or set(base_ref) == {"0"}:
        return set()
    check = subprocess.run(
        ["git", "cat-file", "-e", f"{base_ref}^{{commit}}"], cwd=root,
        capture_output=True,
    )
    if check.returncode:
        raise PolicyError(f"artifact-policy base commit is unavailable: {base_ref}")
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "-z", base_ref, "HEAD"],
        cwd=root, check=True, capture_output=True,
    )
    return {item.decode() for item in result.stdout.split(b"\0") if item}


def evaluate_artifacts(
    root: Path,
    files: Iterable[Path],
    policy: dict[str, Any],
    *,
    changed: set[str] | None = None,
) -> dict[str, Any]:
    threshold = int(policy["threshold_bytes"])
    legacy = {str(path): int(size) for path, size in policy["legacy_large_files"].items()}
    changed = changed or set()
    violations: list[dict[str, Any]] = []
    large_files: list[dict[str, Any]] = []
    for path in files:
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        if size > threshold:
            large_files.append({"path": relative, "bytes": size})
            maximum = legacy.get(relative)
            if maximum is None:
                violations.append({
                    "path": relative,
                    "reason": "new tracked file exceeds large-artifact threshold",
                    "bytes": size,
                })
            elif size > maximum:
                violations.append({
                    "path": relative,
                    "reason": "grandfathered tracked artifact grew beyond its recorded size",
                    "bytes": size,
                    "maximum_bytes": maximum,
                })
        if (
            relative in changed
            and relative.startswith("runs/")
            and path.suffix.lower() in RUN_MEDIA_SUFFIXES
        ):
            violations.append({
                "path": relative,
                "reason": (
                    "new or modified run media belongs in a GitHub release asset, "
                    "Actions artifact, or local/cold storage"
                ),
                "bytes": size,
            })
    return {
        "schema_version": "1.0",
        "gate": "pass" if not violations else "fail",
        "threshold_bytes": threshold,
        "tracked_large_file_count": len(large_files),
        "grandfathered_large_file_count": len(legacy),
        "changed_file_count": len(changed),
        "large_files": sorted(large_files, key=lambda item: item["path"]),
        "violations": violations,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="video-gen-artifact-policy")
    result.add_argument(
        "--policy", default="artifact-policy/legacy-large-files.json"
    )
    result.add_argument("--base-ref")
    result.add_argument("--output")
    return result


def main(argv: Iterable[str] | None = None) -> int:
    args = parser().parse_args(list(argv) if argv is not None else None)
    root = Path.cwd().resolve()
    try:
        policy = load_policy(args.policy)
        report = evaluate_artifacts(
            root,
            tracked_files(root),
            policy,
            changed=changed_files(root, args.base_ref),
        )
    except (OSError, subprocess.CalledProcessError, PolicyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
