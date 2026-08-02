import json
import os
import subprocess
import sys
from decimal import Decimal

from video_gen.ledger import Ledger


def test_audit_export_contains_events_totals_and_media_hash(tmp_path):
    ledger_path = tmp_path / "ledger.sqlite3"
    ledger = Ledger(ledger_path)
    ledger.reserve("request-1", "model", Decimal("0.0125"), Decimal("1"))
    ledger.append("request-1", "completed", actual=Decimal("0.01"))
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / "clip.mp4").write_bytes(b"video")
    destination = tmp_path / "audit.json"

    environment = os.environ.copy()
    environment["PYTHONPATH"] = "src"
    subprocess.run([
        sys.executable, "scripts/export_audit.py", "--ledger", str(ledger_path),
        "--outputs", str(outputs), "--destination", str(destination)
    ], check=True, env=environment)

    packet = json.loads(destination.read_text())
    assert packet["totals"] == {"actual_usd": "0.01", "reserved_usd": "0.0125"}
    assert [event["event"] for event in packet["events"]] == ["reserved", "completed"]
    assert packet["media"][0]["bytes"] == 5
    assert len(packet["media"][0]["sha256"]) == 64
