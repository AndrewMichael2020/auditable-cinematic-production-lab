import json

import pytest

from video_gen.config import ProjectConfig
from video_gen.errors import PolicyError, ProviderError, UnknownBillingStatus
from video_gen.ledger import Ledger
from video_gen.orchestrator import (Orchestrator, audit_safe_url,
                                    reported_cost_exceeds_reservation)
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


def test_audit_safe_url_omits_data_url_payload():
    assert audit_safe_url("data:video/mp4;base64,dmlkZW8=") == \
        "data:video/mp4;base64,[OMITTED]"


def test_failed_download_records_cost_and_provider_provenance(tmp_path):
    app, ledger = setup(tmp_path)
    response = {
        "video_url": "https://example/v.mp4?signature=secret",
        "request_id": "provider-1",
        "inference_status": {"cost": "0.0125"},
    }

    def transport(req, timeout):
        if req.full_url.startswith("https://example/v.mp4"):
            return 503, b"", {}
        return 200, json.dumps(response).encode(), {}

    client = DeepInfraClient("token", transport)
    with pytest.raises(ProviderError, match="503"):
        app.run_video("draft_video", "prompt", live=True, confirmed=True,
                      client=client, output_dir=tmp_path)
    assert str(ledger.actual_total()) == "0.0125"
    event = ledger.db.execute(
        "SELECT metadata FROM events WHERE event='failed'"
    ).fetchone()[0]
    assert "provider-1" in event
    assert "signature" not in event


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


def test_missing_live_token_does_not_reserve(tmp_path, monkeypatch):
    app, ledger = setup(tmp_path)
    monkeypatch.delenv("DEEPINFRA_TOKEN", raising=False)
    with pytest.raises(ProviderError, match="DEEPINFRA_TOKEN"):
        app.run_video("draft_video", "prompt", live=True, confirmed=True)
    assert ledger.reserved_total() == 0


def test_candidate_count_cap_overrides_remaining_money(tmp_path):
    app, ledger = setup(tmp_path)
    model = app.config.model("draft_video")
    for index in range(40):
        ledger.reserve(str(index), model.id, model.reserve(seconds=5), app.cap)
    with pytest.raises(PolicyError, match="candidate cap"):
        app.run_video("draft_video", "one too many")


def test_speech_dry_run_reserves_by_character(tmp_path):
    app, ledger = setup(tmp_path)
    result = app.run_speech("Four")
    assert result.dry_run is True
    assert str(result.reserved_usd) == "0.000004"
    assert ledger.actual_total() == 0


def test_live_speech_persists_wav_and_word_timing(tmp_path):
    app, ledger = setup(tmp_path)
    response = {
        "audio": "UklGRg==",
        "words": [{"start": 0.0, "end": 0.4, "text": "Four"}],
        "request_id": "speech-provider-1",
        "inference_status": {"cost": "0.000004000000000000001"},
    }

    def transport(req, timeout):
        if req.full_url.startswith("data:audio/wav"):
            return None, b"RIFF", {}
        return 200, json.dumps(response).encode(), {}

    result = app.run_speech("Four", live=True, confirmed=True,
                            client=DeepInfraClient("token", transport), output_dir=tmp_path)
    assert result.dry_run is False
    assert (tmp_path / f"{result.request_id}.wav").read_bytes() == b"RIFF"
    assert str(ledger.actual_total()) == "0.000004000000000000001"
    metadata = ledger.db.execute(
        "SELECT metadata FROM events WHERE event='completed'"
    ).fetchone()[0]
    assert "speech-provider-1" in metadata
    assert '"start": 0.0' in metadata


def test_cost_comparison_ignores_float_noise_but_not_real_overage():
    from decimal import Decimal

    reserved = Decimal("0.000035")
    assert reported_cost_exceeds_reservation(
        Decimal("0.000035000000000000004"), reserved
    ) is False
    assert reported_cost_exceeds_reservation(Decimal("0.000036"), reserved) is True


def test_partner_avatar_requires_explicit_override_without_reserving(tmp_path):
    app, ledger = setup(tmp_path)
    with pytest.raises(PolicyError, match="allow-partner-avatar"):
        app.run_avatar("data:image/png;base64,aW1hZ2U=", "Hello", "Kore (Female)")
    assert ledger.reserved_total() == 0


def test_partner_avatar_accepts_public_https_without_persisting_url(tmp_path):
    app, ledger = setup(tmp_path)
    result = app.run_avatar(
        "https://temporary.example/portrait.jpg", "Hello", "Kore (Female)",
        allow_partner=True,
    )
    assert result.dry_run is True
    events = ledger.db.execute("SELECT metadata FROM events ORDER BY sequence").fetchall()
    assert all("temporary.example" not in (row[0] or "") for row in events)


def test_partner_avatar_rejects_insecure_image_url_without_reserving(tmp_path):
    app, ledger = setup(tmp_path)
    with pytest.raises(PolicyError, match="public HTTPS"):
        app.run_avatar(
            "http://temporary.example/portrait.jpg", "Hello", "Kore (Female)",
            allow_partner=True,
        )
    assert ledger.reserved_total() == 0


def test_live_partner_avatar_uses_three_dollar_cap_and_persists_video(tmp_path):
    app, ledger = setup(tmp_path)
    response = {
        "video_url": "data:video/mp4;base64,dmlkZW8=",
        "request_id": "avatar-provider-1",
        "inference_status": {"cost": "0.10"},
    }
    client = DeepInfraClient(
        "token", lambda req, timeout: (200, json.dumps(response).encode(), {})
        if not req.full_url.startswith("data:video") else (None, b"video", {})
    )
    result = app.run_avatar(
        "data:image/png;base64,aW1hZ2U=", "Hello", "Kore (Female)",
        live=True, confirmed=True, allow_partner=True, client=client, output_dir=tmp_path,
    )
    assert result.reserved_usd == app.config.model("lip_sync_avatar").reserve(seconds=8)
    assert (tmp_path / f"{result.request_id}.mp4").read_bytes() == b"video"
    assert str(ledger.actual_total()) == "0.10"
    metadata = ledger.db.execute(
        "SELECT metadata FROM events WHERE event='completed'"
    ).fetchone()[0]
    assert "avatar-provider-1" in metadata
    assert "data:image" not in metadata


def test_partner_avatar_attempt_cap_is_five(tmp_path):
    app, ledger = setup(tmp_path)
    model = app.config.model("lip_sync_avatar")
    for index in range(5):
        ledger.reserve(f"avatar-{index}", model.id, model.reserve(seconds=8), app.cap)
    with pytest.raises(PolicyError, match="avatar request cap"):
        app.run_avatar(
            "https://temporary.example/portrait.jpg", "Hello", "Kore (Female)",
            allow_partner=True,
        )
