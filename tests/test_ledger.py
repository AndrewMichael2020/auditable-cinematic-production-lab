from decimal import Decimal

import pytest

from video_gen.errors import BudgetExceeded, PolicyError
from video_gen.ledger import Ledger


def test_reservation_is_append_only_and_cap_is_conservative(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    ledger.reserve("one", "model", Decimal("0.6"), Decimal("1"))
    ledger.append("one", "completed", actual=Decimal("0.1"))
    assert ledger.reserved_total() == Decimal("0.6")
    assert ledger.actual_total() == Decimal("0.1")
    with pytest.raises(BudgetExceeded):
        ledger.reserve("two", "model", Decimal("0.5"), Decimal("1"))


def test_duplicate_request_is_rejected(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    ledger.reserve("same", "model", Decimal("0.1"), Decimal("1"))
    with pytest.raises(PolicyError, match="duplicate"):
        ledger.reserve("same", "model", Decimal("0.1"), Decimal("1"))


def test_actual_total_includes_failed_billing_and_latest_reconciliation(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    ledger.reserve("failed", "model", Decimal("0.2"), Decimal("1"))
    ledger.append("failed", "failed", actual=Decimal("0.2"))
    assert ledger.actual_total() == Decimal("0.2")

    ledger.append("failed", "completed", actual=Decimal("0.15"))
    assert ledger.actual_total() == Decimal("0.15")
