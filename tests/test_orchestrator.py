import json

import pytest

from video_gen.config import ProjectConfig
from video_gen.errors import PolicyError, UnknownBillingStatus
from video_gen.ledger import Ledger
from video_gen.orchestrator import Orchestrator, audit_safe_url
from video_gen.provider import DeepInfraClient


def setup(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    return Orchestrator(ProjectConfig.load(), ledger, "cad_10"), ledger


def test_dry_run_is_default_and_never_calls_provider(tmp_path):
    app, ledger = setup(tmp_path)
    result = app.run_video("draft_video", "safe prompt", seed=12)
    assert result.dry_run is True
    assert str(result.reserved_usd) == "0.0125"
    assert ledger.actual_total() == 0


def test_final_requires_human_promotion(tmp_path):
    app, _ = setup(tmp_path)
    with pytest.raises(PolicyError, match="human promotion"):
        app.run_video("final_video", "prompt", live=True)


def test_live_reconciles_reported_cost(tmp_path):
    app, ledger = setup(tmp_path)
    response = {"video_url": "https://example/v.mp4?signature=secret", "inference_status": {"cost": "0.01"}}
    def transport(req, timeout):
        if req.full_url == "https://example/v.mp4?signature=secret":
            return 200, b"video bytes", {}
        return 200, json.dumps(response).encode(), {}
    client = DeepInfraClient("token", transport)
    result = app.run_video("draft_video", "prompt", live=True, confirmed=True, client=client, output_dir=tmp_path)
    assert result.dry_run is False
    assert str(ledger.actual_total()) == "0.01"
    event = ledger.db.execute("SELECT metadata FROM events WHERE event='completed'").fetchone()[0]
    assert "output_sha256" in event
    assert "signature" not in event


def test_audit_safe_url_removes_query_and_fragment():
    assert audit_safe_url("https://cdn.example/v.mp4?token=x#part") == "https://cdn.example/v.mp4"


def test_unknown_cost_is_recorded_and_not_retried(tmp_path):
    app, ledger = setup(tmp_path)
    client = DeepInfraClient("token", lambda req, timeout: (200, b'{"video_url":"x"}', {}))
    with pytest.raises(UnknownBillingStatus):
        app.run_video("draft_video", "prompt", live=True, confirmed=True, client=client)
    event = ledger.db.execute("SELECT event FROM events ORDER BY sequence DESC").fetchone()[0]
    assert event == "billing_unknown"


def test_unconfirmed_live_request_does_not_reserve(tmp_path):
    app, ledger = setup(tmp_path)
    with pytest.raises(PolicyError, match="confirm-live"):
        app.run_video("draft_video", "prompt", live=True)
    assert ledger.reserved_total() == 0


def test_candidate_count_cap_overrides_remaining_money(tmp_path):
    app, ledger = setup(tmp_path)
    model = app.config.model("draft_video")
    for index in range(40):
        ledger.reserve(str(index), model.id, model.reserve(seconds=5), app.cap)
    with pytest.raises(PolicyError, match="candidate cap"):
        app.run_video("draft_video", "one too many")
