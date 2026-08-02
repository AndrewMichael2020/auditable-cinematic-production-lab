#!/usr/bin/env python3
"""Export a deterministic, human-readable audit packet for a live smoke run."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from video_gen.ledger import Ledger


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", required=True)
    parser.add_argument("--outputs", required=True)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()

    ledger = Ledger(args.ledger)
    output_dir = Path(args.outputs)
    media = [
        {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(output_dir.glob("*.mp4"))
    ]
    packet = {
        "schema_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "events": ledger.audit_events(),
        "totals": {
            "reserved_usd": str(ledger.reserved_total()),
            "actual_usd": str(ledger.actual_total()),
        },
        "media": media,
    }
    destination = Path(args.destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
