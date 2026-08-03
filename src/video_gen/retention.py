from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .errors import PolicyError


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_recomputable(path: Path) -> tuple[bool, str]:
    name = path.name.lower()
    parents = {part.lower() for part in path.parts}
    if any(part == "frames" or part.endswith("-frames") for part in parents):
        return True, "sampled frame; regenerate from retained source media"
    if "preview" in name:
        return True, "visual preview; regenerate from retained source media"
    if ("all-frames" in name or "every-other-frame" in name or
            ("contact" in name and "final-contact-sheet" not in name)):
        return True, "intermediate contact sheet; regenerate from retained source media"
    if name.endswith(".stdout.json"):
        return True, "duplicate CLI stdout; canonical JSON report is retained"
    if name.endswith(".exit-code.txt"):
        return True, "transient command exit code; canonical QA report is retained"
    if name.endswith("decode-check.txt") or "black-freeze-check" in name:
        return True, "FFmpeg diagnostic; regenerate from retained media"
    if name in {"output-files.txt", "partial-output-files.txt", "sha256sums.partial"}:
        return True, "transient inventory superseded by canonical manifest"
    return False, ""


def _retention_reason(path: Path) -> str:
    name = path.name.lower()
    if path.suffix == ".sqlite3":
        return "append-only cost and provenance ledger"
    if path.suffix.lower() in {".mp4", ".wav"}:
        return "source or accepted media required for playback and re-editing"
    if "contact-sheet" in name:
        return "compact visual review evidence"
    if any(term in name for term in ("manifest", "audit", "report", "qa", "model-info",
                                     "scene", "observations", "pytest", "sha256")):
        return "compact reproducibility or audit evidence"
    if name.endswith(("-compact.jpg", "-compact.png", "-compact.webp")):
        return "selected compact actor reference"
    return "unclassified; retained fail-closed"


def audit_run_artifacts(run: str | Path) -> dict[str, Any]:
    root = Path(run)
    if not root.is_dir():
        raise PolicyError(f"run directory does not exist: {root}")
    files: list[dict[str, Any]] = []
    totals = {"retain_bytes": 0, "recomputable_bytes": 0}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        recomputable, reason = _is_recomputable(path.relative_to(root))
        category = "recomputable" if recomputable else "retain"
        size = path.stat().st_size
        totals[f"{category}_bytes"] += size
        files.append({
            "path": str(path),
            "relative_path": str(path.relative_to(root)),
            "bytes": size,
            "sha256": _sha256(path),
            "category": category,
            "reason": reason if recomputable else _retention_reason(path),
        })
    return {
        "schema_version": "1.0",
        "run": str(root),
        "policy": "retain source/final media plus compact audit evidence; prune only deterministic derivatives",
        "files": files,
        "summary": {
            **totals,
            "file_count": len(files),
            "retain_count": sum(item["category"] == "retain" for item in files),
            "recomputable_count": sum(item["category"] == "recomputable" for item in files),
        },
    }


def prune_recomputable_artifacts(run: str | Path, *, apply: bool = False) -> dict[str, Any]:
    report = audit_run_artifacts(run)
    candidates = [item for item in report["files"] if item["category"] == "recomputable"]
    removed: list[str] = []
    if apply:
        root = Path(run).resolve()
        for item in candidates:
            target = Path(item["path"]).resolve()
            if root not in target.parents or not target.is_file():
                raise PolicyError("refusing to prune a path outside the resolved run directory")
            target.unlink()
            removed.append(str(target))
        for directory in sorted((item for item in root.rglob("*") if item.is_dir()), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass
    return {
        "schema_version": "1.0",
        "run": report["run"],
        "mode": "applied" if apply else "dry_run",
        "candidate_count": len(candidates),
        "reclaimable_bytes": sum(item["bytes"] for item in candidates),
        "candidates": [{key: item[key] for key in ("relative_path", "bytes", "sha256", "reason")}
                       for item in candidates],
        "removed": removed,
    }
