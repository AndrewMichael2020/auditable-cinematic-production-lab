from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from .errors import BudgetExceeded, PolicyError


@dataclass(frozen=True)
class Entry:
    request_id: str
    status: str
    model: str
    reserved_usd: Decimal
    actual_usd: Decimal | None


class Ledger:
    """Append-only event ledger; current entries are derived from immutable events."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""CREATE TABLE IF NOT EXISTS events (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL,
          event TEXT NOT NULL, model TEXT NOT NULL, reserved_usd TEXT NOT NULL,
          actual_usd TEXT, metadata TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
          DEFAULT CURRENT_TIMESTAMP)""")
        self.db.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_reservation ON events(request_id) WHERE event='reserved'")
        self.db.commit()

    def reserve(self, request_id: str, model: str, amount: Decimal, cap: Decimal) -> None:
        if amount < 0:
            raise PolicyError("reservation cannot be negative")
        try:
            with self.db:
                existing = self.db.execute("SELECT 1 FROM events WHERE request_id=?", (request_id,)).fetchone()
                if existing:
                    raise PolicyError(f"duplicate request id: {request_id}")
                total = self.reserved_total()
                if total + amount > cap:
                    raise BudgetExceeded(f"reservation {amount} would exceed USD {cap} cap")
                self.db.execute("INSERT INTO events(request_id,event,model,reserved_usd) VALUES(?, 'reserved', ?, ?)",
                                (request_id, model, str(amount)))
        except sqlite3.IntegrityError as exc:
            raise PolicyError(f"duplicate request id: {request_id}") from exc

    def append(self, request_id: str, event: str, *, actual: Decimal | None = None,
               metadata: str = "{}") -> None:
        row = self.db.execute("SELECT model,reserved_usd FROM events WHERE request_id=? AND event='reserved'",
                              (request_id,)).fetchone()
        if not row:
            raise PolicyError(f"request was not reserved: {request_id}")
        if event not in {"completed", "failed", "billing_unknown"}:
            raise PolicyError(f"invalid ledger event: {event}")
        with self.db:
            self.db.execute("INSERT INTO events(request_id,event,model,reserved_usd,actual_usd,metadata) VALUES(?,?,?,?,?,?)",
                            (request_id, event, row[0], row[1], None if actual is None else str(actual), metadata))

    def reserved_total(self) -> Decimal:
        # Reservations remain charged against this run's cap even after reconciliation.
        rows = self.db.execute("SELECT reserved_usd FROM events WHERE event='reserved'")
        return sum((Decimal(row[0]) for row in rows), Decimal("0"))

    def actual_total(self) -> Decimal:
        rows = self.db.execute("SELECT actual_usd FROM events WHERE event='completed' AND actual_usd IS NOT NULL")
        return sum((Decimal(row[0]) for row in rows), Decimal("0"))

    def reservation_count(self, model: str) -> int:
        return int(self.db.execute("SELECT COUNT(*) FROM events WHERE event='reserved' AND model=?",
                                   (model,)).fetchone()[0])

    def audit_events(self) -> list[dict[str, Any]]:
        """Return the immutable event stream in a portable, ordered form."""
        columns = ("sequence", "request_id", "event", "model", "reserved_usd",
                   "actual_usd", "metadata", "created_at")
        rows = self.db.execute(
            "SELECT sequence,request_id,event,model,reserved_usd,actual_usd,metadata,created_at "
            "FROM events ORDER BY sequence"
        )
        return [dict(zip(columns, row, strict=True)) for row in rows]

    def close(self) -> None:
        self.db.close()
