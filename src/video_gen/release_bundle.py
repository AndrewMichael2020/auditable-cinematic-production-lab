from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .errors import PolicyError
from .secret_scan import PATTERNS


FIXED_ZIP_TIME = (2026, 8, 15, 0, 0, 0)
MAX_MEMBER_BYTES = 2 * 1024 * 1024
MAX_BUNDLE_BYTES = 8 * 1024 * 1024
FORBIDDEN_SUFFIXES = {
    ".aac", ".avi", ".db", ".gz", ".jpg", ".jpeg", ".mkv", ".mov",
    ".mp3", ".mp4", ".png", ".sqlite", ".sqlite3", ".tar", ".wav", ".webp",
}
REQUIRED_FILES = (
    "LICENSE",
    "README.md",
    "pyproject.toml",
    "project.json",
    "docs/ARTIFACT-STRATEGY.md",
    "docs/PROVIDER-SNAPSHOT-2026-08-15.md",
    "docs/REPRODUCIBILITY.md",
    "examples/portfolio-dry-run/README.md",
    "examples/portfolio-dry-run/scene.json",
    "examples/portfolio-dry-run/av-sync-calibration.json",
    "examples/portfolio-dry-run/expected/preflight.json",
    "examples/portfolio-dry-run/expected/av-sync-calibration-report.json",
    "runs/clinic-stage2-20260803T060048Z/RUN-REPORT.md",
    "runs/clinic-stage2-20260803T060048Z/audits/final-stage2-audit-v3.json",
    "runs/clinic-stage2-20260803T060048Z/audits/final-stage2-observations-v3.json",
    "runs/clinic-stage2-20260803T060048Z/final/clinic-stage2-sequence-v3-manifest.json",
    "runs/clinic-stage2-20260803T060048Z/final/final-timeline.json",
)
SOURCE_GLOBS = ("src/video_gen/*.py",)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_version(root: Path) -> str:
    packet = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    version = str(packet.get("project", {}).get("version", "")).strip()
    if not version:
        raise PolicyError("pyproject.toml does not declare project.version")
    return version


def release_files(root: Path) -> list[Path]:
    paths = [root / item for item in REQUIRED_FILES]
    for pattern in SOURCE_GLOBS:
        paths.extend(root.glob(pattern))
    missing = [str(path.relative_to(root)) for path in paths if not path.is_file()]
    if missing:
        raise PolicyError(f"release inputs are missing: {', '.join(sorted(missing))}")
    unique = sorted(set(paths), key=lambda path: path.relative_to(root).as_posix())
    for path in unique:
        relative = path.relative_to(root)
        if path.stat().st_size > MAX_MEMBER_BYTES:
            raise PolicyError(f"release member exceeds 2 MiB: {relative}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise PolicyError(f"media, archives, and databases are excluded from the bundle: {relative}")
    return unique


def _credential_findings(name: str, data: bytes) -> list[str]:
    return [label for label, pattern in PATTERNS.items() if pattern.search(data)]


def _write_member(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build_release_bundle(root: str | Path, output: str | Path) -> dict[str, Any]:
    root_path = Path(root).resolve()
    output_path = Path(output).resolve()
    version = project_version(root_path)
    files = release_files(root_path)
    entries: list[dict[str, Any]] = []
    data_by_name: dict[str, bytes] = {}
    for path in files:
        name = path.relative_to(root_path).as_posix()
        data = path.read_bytes()
        findings = _credential_findings(name, data)
        if findings:
            raise PolicyError(
                f"release credential scan blocked {name}: {', '.join(findings)}"
            )
        data_by_name[name] = data
        entries.append({"path": name, "bytes": len(data), "sha256": sha256_bytes(data)})

    manifest = {
        "schema_version": "1.0",
        "project": "cinematic-production-lab",
        "release_version": version,
        "bundle_scope": (
            "CLI source, policy, zero-cost sample, expected output, provider snapshot, "
            "and bounded accepted-run JSON/Markdown evidence; no media, database, credential, "
            "signed URL, or private/local-only artifact"
        ),
        "accepted_media_external": {
            "youtube": "https://www.youtube.com/watch?v=VnIrfT_vzvI",
            "repository_path": (
                "runs/clinic-stage2-20260803T060048Z/final/"
                "clinic-stage2-sequence-v3.mp4"
            ),
        },
        "entries": entries,
    }
    manifest_data = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    if _credential_findings("MANIFEST.json", manifest_data):
        raise PolicyError("generated release manifest contains credential-shaped material")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=output_path.parent, prefix=f".{output_path.name}.", suffix=".tmp", delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with zipfile.ZipFile(temporary_path, "w") as archive:
            members = {**data_by_name, "MANIFEST.json": manifest_data}
            for name in sorted(members):
                _write_member(archive, name, members[name])
        if temporary_path.stat().st_size > MAX_BUNDLE_BYTES:
            raise PolicyError("release bundle exceeds the 8 MiB bounded-size limit")
        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    digest = sha256_file(output_path)
    checksum_path = output_path.with_name(f"{output_path.name}.sha256")
    checksum_path.write_text(f"{digest}  {output_path.name}\n", encoding="utf-8")
    return {
        "ok": True,
        "release_version": version,
        "bundle": str(output_path),
        "bundle_bytes": output_path.stat().st_size,
        "bundle_sha256": digest,
        "checksum": str(checksum_path),
        "member_count": len(entries) + 1,
    }


def verify_release_bundle(path: str | Path) -> dict[str, Any]:
    bundle = Path(path).resolve()
    if not bundle.is_file():
        raise PolicyError(f"release bundle does not exist: {bundle}")
    if bundle.stat().st_size > MAX_BUNDLE_BYTES:
        raise PolicyError("release bundle exceeds the 8 MiB bounded-size limit")
    with zipfile.ZipFile(bundle) as archive:
        names = archive.namelist()
        if names != sorted(names) or len(names) != len(set(names)):
            raise PolicyError("release members must be unique and sorted")
        if "MANIFEST.json" not in names:
            raise PolicyError("release bundle is missing MANIFEST.json")
        total_uncompressed = 0
        for name in names:
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts:
                raise PolicyError(f"unsafe release member path: {name}")
            if pure.suffix.lower() in FORBIDDEN_SUFFIXES:
                raise PolicyError(f"forbidden media/archive/database member: {name}")
            info = archive.getinfo(name)
            if info.flag_bits & 0x1:
                raise PolicyError(f"encrypted release member is not allowed: {name}")
            if info.file_size > MAX_MEMBER_BYTES:
                raise PolicyError(f"release member exceeds 2 MiB: {name}")
            total_uncompressed += info.file_size
        if total_uncompressed > MAX_BUNDLE_BYTES:
            raise PolicyError("release bundle exceeds the 8 MiB uncompressed limit")
        manifest_data = archive.read("MANIFEST.json")
        if _credential_findings("MANIFEST.json", manifest_data):
            raise PolicyError("release manifest contains credential-shaped material")
        manifest = json.loads(manifest_data)
        expected = {item["path"]: item for item in manifest.get("entries", [])}
        actual_names = set(names) - {"MANIFEST.json"}
        if actual_names != set(expected):
            raise PolicyError("release manifest does not exactly match bundle members")
        for name in sorted(actual_names):
            data = archive.read(name)
            item = expected[name]
            if len(data) != int(item["bytes"]) or sha256_bytes(data) != item["sha256"]:
                raise PolicyError(f"release member hash mismatch: {name}")
            findings = _credential_findings(name, data)
            if findings:
                raise PolicyError(
                    f"release credential scan blocked {name}: {', '.join(findings)}"
                )
    return {
        "ok": True,
        "bundle": str(bundle),
        "bundle_bytes": bundle.stat().st_size,
        "bundle_sha256": sha256_file(bundle),
        "release_version": manifest["release_version"],
        "member_count": len(names),
        "credential_scan": "pass",
        "media_exclusion": "pass",
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="video-gen-release")
    commands = result.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="build a deterministic bounded release bundle")
    build.add_argument("--root", default=".")
    build.add_argument("--output")
    verify = commands.add_parser("verify", help="verify bundle members, hashes, and exclusions")
    verify.add_argument("bundle")
    return result


def emit(packet: dict[str, Any]) -> None:
    print(json.dumps(packet, indent=2, sort_keys=True))


def main(argv: Iterable[str] | None = None) -> int:
    args = parser().parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "build":
            root = Path(args.root).resolve()
            version = project_version(root)
            output = (
                Path(args.output)
                if args.output
                else root / "dist" / f"cinematic-production-lab-v{version}.zip"
            )
            emit(build_release_bundle(root, output))
        else:
            emit(verify_release_bundle(args.bundle))
        return 0
    except (OSError, ValueError, zipfile.BadZipFile, PolicyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
