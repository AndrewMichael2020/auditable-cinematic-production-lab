from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Iterable


PATTERNS = {
    "GitHub token": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{70,})"),
    "OpenAI-style key": re.compile(rb"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    "Google API key": re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "assigned DeepInfra token": re.compile(
        rb"DEEPINFRA_(?:API_)?TOKEN\s*[=:]\s*['\"]?[A-Za-z0-9_-]{20,}"
    ),
}
MAX_TEXT_BYTES = 2_000_000


def scan_files(paths: Iterable[Path]) -> list[tuple[Path, str]]:
    findings: list[tuple[Path, str]] = []
    for path in paths:
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if len(data) > MAX_TEXT_BYTES or b"\0" in data:
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(data):
                findings.append((path, label))
    return findings


def tracked_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, check=True, capture_output=True,
    )
    return [root / item.decode() for item in result.stdout.split(b"\0") if item]


def main() -> int:
    root = Path.cwd()
    findings = scan_files(tracked_files(root))
    for path, label in findings:
        print(f"possible {label}: {path.relative_to(root)}", file=sys.stderr)
    if findings:
        print(f"blocked: {len(findings)} tracked credential finding(s)", file=sys.stderr)
        return 1
    print("tracked credential scan passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
