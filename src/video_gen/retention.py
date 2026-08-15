from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .errors import PolicyError


REJECTED_MEDIA_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".wav", ".flac"}


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


def prune_rejected_media(
    run: str | Path,
    decisions: str | Path,
    *,
    minimum_bytes: int = 25 * 1024 * 1024,
    apply: bool = False,
) -> dict[str, Any]:
    """Prune only large media named in an evidence-backed rejection manifest."""
    root = Path(run).resolve()
    if not root.is_dir():
        raise PolicyError(f"run directory does not exist: {root}")
    if minimum_bytes < 0:
        raise PolicyError("minimum rejected-media size cannot be negative")
    decisions_path = Path(decisions)
    try:
        packet = json.loads(decisions_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError("rejected-media decisions must be readable JSON") from exc
    if not isinstance(packet, dict) or packet.get("schema_version") != "1.0":
        raise PolicyError("rejected-media decisions require schema_version 1.0")
    entries = packet.get("decisions")
    protected = packet.get("protected_paths", [])
    if not isinstance(entries, list) or not isinstance(protected, list):
        raise PolicyError("rejected-media decisions require decisions and protected_paths")
    protected_paths = {str(item) for item in protected}

    candidates: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise PolicyError("rejected-media decision must be an object")
        relative = str(entry.get("relative_path", "")).strip()
        outcome = str(entry.get("outcome", "")).strip()
        reason = str(entry.get("reason", "")).strip()
        expected_sha = str(entry.get("sha256", "")).strip()
        evidence = entry.get("retained_evidence")
        if outcome not in {"failed", "rejected"} or not relative or not reason:
            raise PolicyError("rejected-media decision is incomplete")
        if relative in protected_paths or "anchor" in Path(relative).name.lower():
            raise PolicyError(f"rejected-media decision targets protected media: {relative}")
        if not isinstance(evidence, list) or not evidence:
            raise PolicyError("rejected-media deletion requires retained evidence")
        target = (root / relative).resolve()
        if root not in target.parents or not target.is_file():
            raise PolicyError("rejected-media target must be an existing file inside the run")
        if target.suffix.lower() not in REJECTED_MEDIA_EXTENSIONS:
            raise PolicyError("rejected-media target must be a supported large media file")
        actual_sha = _sha256(target)
        if expected_sha != actual_sha:
            raise PolicyError("rejected-media SHA-256 does not match")
        evidence_paths: list[str] = []
        for evidence_relative in evidence:
            evidence_path = (root / str(evidence_relative)).resolve()
            if (
                root not in evidence_path.parents
                or not evidence_path.is_file()
                or evidence_path == target
            ):
                raise PolicyError("rejected-media evidence must be a retained file inside the run")
            evidence_paths.append(str(evidence_path.relative_to(root)))
        if target.stat().st_size < minimum_bytes:
            continue
        candidates.append({
            "relative_path": relative,
            "bytes": target.stat().st_size,
            "sha256": actual_sha,
            "outcome": outcome,
            "reason": reason,
            "retained_evidence": evidence_paths,
        })

    removed: list[str] = []
    if apply:
        for item in candidates:
            target = (root / item["relative_path"]).resolve()
            if root not in target.parents or not target.is_file():
                raise PolicyError("refusing to prune a path outside the resolved run directory")
            target.unlink()
            removed.append(str(target))
    return {
        "schema_version": "1.0",
        "run": str(root),
        "decision_manifest": str(decisions_path),
        "mode": "applied" if apply else "dry_run",
        "policy": "delete only explicitly failed/rejected large media with hash and retained evidence",
        "minimum_bytes": minimum_bytes,
        "candidate_count": len(candidates),
        "reclaimable_bytes": sum(item["bytes"] for item in candidates),
        "candidates": candidates,
        "removed": removed,
    }
