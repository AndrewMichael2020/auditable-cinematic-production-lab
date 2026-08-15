import json
import ssl
import urllib.error
from decimal import Decimal

import pytest

from video_gen.config import ProjectConfig
from video_gen.elevenlabs import ElevenLabsClient
from video_gen.errors import PolicyError, ProviderError, UnknownBillingStatus
from video_gen.ledger import Ledger
from video_gen.orchestrator import (Orchestrator, audit_safe_url,
                                    reported_cost_exceeds_reservation)
from video_gen.provider import DeepInfraClient


def setup(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    return Orchestrator(ProjectConfig.load(), ledger, "cad_10"), ledger


def approved_voice(model_id, provider_voice, **settings):
    return {
        "voice_realization_id": "vr-test-approved-v1",
        "effective_persona_version": "pv01",
        "provider_model_id": model_id,
        "provider_voice": provider_voice,
        "immutable_settings": settings or {"seed": 0},
        "approval": {
            "status": "approved",
            "audition_path": "auditions/test.wav",
            "audition_sha256": "a" * 64,
            "reviewed_by": "test-reviewer",
            "reviewed_at": "2026-08-15T00:00:00Z",
        },
    }


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
    response = {
        "video_url": "https://example/v.mp4?signature=secret",
        "request_id": "provider-request-1",
        "inference_status": {"cost": "0.01"},
    }

    request_payloads = []

    def transport(req, timeout):
        if req.full_url == "https://example/v.mp4?signature=secret":
            return 200, b"video bytes", {}
        request_payloads.append(json.loads(req.data))
        return 200, json.dumps(response).encode(), {}

    client = DeepInfraClient("token", transport)
    result = app.run_video("draft_video", "prompt", live=True, confirmed=True, client=client, output_dir=tmp_path)
    assert result.dry_run is False
    assert result.output_path == str(tmp_path / f"{result.request_id}.mp4")
    assert result.output_sha256
    assert result.provider_request_id
    assert str(ledger.actual_total()) == "0.01"
    event = ledger.db.execute("SELECT metadata FROM events WHERE event='completed'").fetchone()[0]
    assert "output_sha256" in event
    assert "signature" not in event
    assert request_payloads == [{
        "prompt": "prompt", "seconds": 5, "resolution": "480p",
        "orientation": "landscape", "seed": 0,
    }]


def test_final_uses_approved_negative_prompt_and_native_landscape_parameters(tmp_path):
    app, _ = setup(tmp_path)
    payloads = []
    response = {"video_url": "data:video/mp4;base64,dmlkZW8=",
                "inference_status": {"cost": "0.375"}}

    def transport(req, timeout):
        if req.full_url.startswith("data:video"):
            return None, b"video", {}
        payloads.append((json.loads(req.data), timeout))
        return 200, json.dumps(response).encode(), {}

    app.run_video(
        "final_video", "cinematic clinic", live=True, confirmed=True,
        client=DeepInfraClient("token", transport), output_dir=tmp_path,
    )

    payload, timeout = payloads[0]
    assert payload["seconds"] == 5
    assert payload["resolution"] == "720p"
    assert payload["orientation"] == "landscape"
    assert "advertisement" in payload["negative_prompt"]
    assert "Vibrant colors" not in payload["negative_prompt"]
    assert timeout == 600


def test_cosmos_super_uses_documented_world_model_payload_and_price(tmp_path):
    app, ledger = setup(tmp_path)
    payloads = []
    response = {
        "video_url": "data:video/mp4;base64,dmlkZW8=",
        "request_id": "cosmos-provider-1",
        "inference_status": {"cost": "0.25"},
    }

    def transport(req, timeout):
        if req.full_url.startswith("data:video"):
            return None, b"video", {}
        payloads.append((req.full_url, json.loads(req.data), timeout))
        return 200, json.dumps(response).encode(), {}

    result = app.run_video(
        "cosmos_world_video", "A locked wide shot with coherent room geometry.",
        seed=42, live=True, confirmed=True,
        client=DeepInfraClient("token", transport), output_dir=tmp_path,
    )

    assert result.model == "nvidia/Cosmos3-Super"
    assert result.reserved_usd == Decimal("0.25")
    assert ledger.actual_total() == Decimal("0.25")
    url, payload, timeout = payloads[0]
    assert url.endswith("/nvidia/Cosmos3-Super")
    assert payload == {
        "prompt": "A locked wide shot with coherent room geometry.",
        "output_type": "video",
        "resolution": "720p",
        "aspect_ratio": "16:9",
        "duration_seconds": 5,
        "seed": 42,
    }
    assert timeout == 900


def test_cosmos_super_webhook_completes_without_long_lived_request(tmp_path):
    app, ledger = setup(tmp_path)
    callback = tmp_path / "callback.json"
    payloads = []

    def transport(req, timeout):
        if req.full_url.startswith("data:video"):
            return None, b"video", {}
        payload = json.loads(req.data)
        payloads.append(payload)
        callback.write_text(json.dumps({
            "request_id": "cosmos-queued-1",
            "inference_status": {"status": "succeeded", "cost": "0.25"},
            "results": {"video": "data:video/mp4;base64,dmlkZW8="},
        }), encoding="utf-8")
        return 200, json.dumps({
            "request_id": "cosmos-queued-1",
            "inference_status": {"status": "queued"},
        }).encode(), {}

    result = app.run_video(
        "cosmos_world_video",
        "A locked clinic.",
        live=True,
        confirmed=True,
        client=DeepInfraClient("token", transport),
        output_dir=tmp_path,
        webhook_url="https://example.test/webhook/token",
        webhook_result_path=callback,
        webhook_wait_seconds=30,
    )
    assert result.dry_run is False
    assert ledger.actual_total() == Decimal("0.25")
    assert payloads[0]["webhook"] == "https://example.test/webhook/token"


def test_cosmos_super_rejects_unbounded_prompt(tmp_path):
    app, ledger = setup(tmp_path)
    with pytest.raises(PolicyError, match="world-model prompt"):
        app.run_video("cosmos_world_video", "")
    assert ledger.reserved_total() == 0


def test_cosmos_super_accepts_inline_anchor_without_persisting_it(tmp_path):
    app, ledger = setup(tmp_path)
    image = "data:image/png;base64,YW5jaG9y"
    result = app.run_video(
        "cosmos_world_video", "Preserve the clinic geometry.", image_input=image,
    )
    assert result.reserved_usd == Decimal("0.25")
    event = ledger.db.execute(
        "SELECT metadata FROM events WHERE event='reserved'"
    ).fetchone()[0]
    assert image not in (event or "")


def voice_spec(script="Hello, Maya."):
    return {
        "character_id": "nurse-maya",
        "persona_version": "pv01",
        "voice_persona_id": "vp-maya-v01",
        "voice_realization_id": "vr-maya-test-v01",
        "model_id": "Qwen/Qwen3-TTS",
        "model_version": "COMBINED_SMALL",
        "synthesis_settings": {
            "voice": "Serena",
            "instruct": "A grounded adult Canadian woman.",
            "language": "English",
            "response_format": "wav",
        },
        "script": script,
    }


def dialogue_spec():
    return {
        "sequence_id": "clinic-sequence",
        "candidate_id": "clinic-dialogue-c01",
        "model_id": "eleven_v3",
        "language_code": "en",
        "output_format": "wav_24000",
        "apply_text_normalization": "auto",
        "seed": 3407,
        "inputs": [
            {"text": "[warmly] Hello.", "voice_id": "sarah"},
            {"text": "[gently] Hello.", "voice_id": "bill"},
        ],
        "turns": [
            {"dialogue_id": "one", "speaker": "maya"},
            {"dialogue_id": "two", "speaker": "kenji"},
        ],
    }


def test_voice_audition_dry_run_reserves_by_character_count(tmp_path):
    app, ledger = setup(tmp_path)
    result = app.run_voice_audition(voice_spec())
    assert result.dry_run is True
    assert result.reserved_usd == Decimal("0.00024")
    assert ledger.actual_total() == 0


def test_live_voice_audition_persists_immutable_wav_and_lineage(tmp_path):
    app, ledger = setup(tmp_path)
    payloads = []
    response = {
        "audio": "UklGRg==",
        "request_id": "voice-provider-1",
        "inference_status": {"cost": "0.00024"},
    }

    def transport(req, timeout):
        if req.full_url.startswith("data:audio/wav"):
            return None, b"RIFF", {}
        payloads.append((req.full_url, json.loads(req.data), timeout))
        return 200, json.dumps(response).encode(), {}

    result = app.run_voice_audition(
        voice_spec(), live=True, confirmed=True,
        client=DeepInfraClient("token", transport), output_dir=tmp_path,
    )

    output = tmp_path / "vr-maya-test-v01.wav"
    assert output.read_bytes() == b"RIFF"
    assert result.output_path == str(output)
    assert result.output_sha256
    assert result.provider_request_id == "voice-provider-1"
    assert payloads == [(
        "https://api.deepinfra.com/v1/inference/Qwen/Qwen3-TTS?version=COMBINED_SMALL",
        {
        "input": "Hello, Maya.",
        "voice": "Serena",
        "instruct": "A grounded adult Canadian woman.",
        "language": "English",
        "response_format": "wav",
        }, 300.0,
    )]
    metadata = ledger.db.execute(
        "SELECT metadata FROM events WHERE event='completed'"
    ).fetchone()[0]
    assert "voice-provider-1" in metadata
    assert "A grounded adult Canadian woman" not in metadata


def test_voice_audition_refuses_to_overwrite_realization(tmp_path):
    app, ledger = setup(tmp_path)
    (tmp_path / "vr-maya-test-v01.wav").write_bytes(b"existing")
    with pytest.raises(PolicyError, match="already exists"):
        app.run_voice_audition(voice_spec(), output_dir=tmp_path)
    assert ledger.reserved_total() == 0


def test_dialogue_candidate_dry_run_reserves_zero_usd_and_no_credits(tmp_path):
    app, ledger = setup(tmp_path)
    result = app.run_dialogue_candidate(dialogue_spec(), output_dir=tmp_path)
    assert result.dry_run is True
    assert result.reserved_usd == Decimal("0.0")
    assert result.character_cost is None
    assert ledger.actual_total() == 0


def test_live_dialogue_candidate_requires_current_pricing_before_reservation(tmp_path):
    app, ledger = setup(tmp_path)
    app.config.raw["pricing"]["verified_at"] = "2020-01-01"
    client = ElevenLabsClient(
        "key", transport=lambda req, timeout: (500, b"", {})
    )
    with pytest.raises(PolicyError, match="pricing snapshot.*stale"):
        app.run_dialogue_candidate(
            dialogue_spec(), live=True, confirmed=True, client=client,
            output_dir=tmp_path,
        )
    assert ledger.reserved_total() == 0


def test_live_dialogue_candidate_persists_wav_timestamps_and_credit_usage(tmp_path):
    app, ledger = setup(tmp_path)
    response = {
        "audio_base64": "UklGRmF1ZGlv",
        "voice_segments": [
            {"voice_id": "sarah", "start_time_seconds": 0.0, "end_time_seconds": 1.0},
            {"voice_id": "bill", "start_time_seconds": 1.2, "end_time_seconds": 2.3},
        ],
        "alignment": {"characters": ["H"]},
    }

    def transport(req, timeout):
        return 200, json.dumps(response).encode(), {
            "request-id": "eleven-request-1",
            "character-cost": "34",
        }

    result = app.run_dialogue_candidate(
        dialogue_spec(), live=True, confirmed=True,
        client=ElevenLabsClient("key", transport=transport), output_dir=tmp_path,
    )
    output = tmp_path / "clinic-dialogue-c01.wav"
    manifest_path = tmp_path / "clinic-dialogue-c01.manifest.json"
    assert output.read_bytes() == b"RIFFaudio"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["character_cost"] == 34
    assert len(manifest["voice_segments"]) == 2
    assert manifest["human_review"]["decision"] == "pending"
    assert result.output_sha256 == manifest["output_sha256"]
    event = ledger.db.execute(
        "SELECT metadata FROM events WHERE event='completed'"
    ).fetchone()[0]
    assert "elevenlabs_credits" in event
    assert "[warmly] Hello" not in event


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


def test_pre_send_tls_verification_failure_is_not_misclassified_as_billable(tmp_path):
    app, ledger = setup(tmp_path)

    def transport(req, timeout):
        certificate_error = ssl.SSLCertVerificationError(
            1, "unable to get local issuer certificate"
        )
        raise urllib.error.URLError(certificate_error)

    with pytest.raises(ProviderError, match="before request submission"):
        app.run_video(
            "draft_video", "prompt", live=True, confirmed=True,
            client=DeepInfraClient("token", transport),
        )
    event = ledger.db.execute(
        "SELECT event FROM events ORDER BY sequence DESC"
    ).fetchone()[0]
    assert event == "failed"
    assert ledger.actual_total() == 0


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

    result = app.run_speech(
        "Four", live=True, confirmed=True,
        voice_realization=approved_voice(
            "ResembleAI/chatterbox-turbo", "test-performance", seed=0,
            response_format="wav",
        ),
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


def test_live_voice_generation_requires_approved_binding_before_reservation(tmp_path):
    app, ledger = setup(tmp_path)
    with pytest.raises(PolicyError, match="approved voice realization"):
        app.run_speech(
            "Four", live=True, confirmed=True,
            client=DeepInfraClient("token", lambda req, timeout: (500, b"", {})),
        )
    assert ledger.reserved_total() == 0


def test_partner_i2v_requires_explicit_override_without_reserving(tmp_path):
    app, ledger = setup(tmp_path)
    with pytest.raises(PolicyError, match="allow-partner-i2v"):
        app.run_image_video(
            "data:image/png;base64,aW1hZ2U=", "Preserve the exact locked composition."
        )
    assert ledger.reserved_total() == 0


def test_live_partner_i2v_uses_locked_payload_and_persists_video(tmp_path):
    app, ledger = setup(tmp_path)
    payloads = []
    response = {
        "video_url": "data:video/mp4;base64,dmlkZW8=",
        "request_id": "i2v-provider-1",
        "inference_status": {"cost": "0.50"},
    }

    def transport(req, timeout):
        if req.full_url.startswith("data:video"):
            return None, b"video", {}
        payloads.append((json.loads(req.data), timeout))
        return 200, json.dumps(response).encode(), {}

    result = app.run_image_video(
        "https://temporary.example/wide-clinic.png",
        "Preserve the exact locked composition and animate one card handoff.",
        audio_input="https://temporary.example/greeting.wav",
        live=True, confirmed=True, allow_partner=True,
        client=DeepInfraClient("token", transport), output_dir=tmp_path,
    )

    assert result.reserved_usd == Decimal("0.50")
    assert result.output_path == str(tmp_path / f"{result.request_id}.mp4")
    assert result.output_sha256
    assert result.provider_request_id == "i2v-provider-1"
    assert (tmp_path / f"{result.request_id}.mp4").read_bytes() == b"video"
    payload, timeout = payloads[0]
    assert payload["resolution"] == "720P"
    assert payload["duration"] == 5
    assert payload["shot_type"] == "single"
    assert payload["prompt_extend"] is False
    assert payload["watermark"] is False
    assert payload["img_url"] == "https://temporary.example/wide-clinic.png"
    assert payload["audio_url"] == "https://temporary.example/greeting.wav"
    assert "moving keyboard" in payload["negative_prompt"]
    assert timeout == 600
    metadata = ledger.db.execute(
        "SELECT metadata FROM events WHERE event='completed'"
    ).fetchone()[0]
    assert "i2v-provider-1" in metadata
    assert "temporary.example" not in metadata
    assert '"image_sha256"' in metadata
    assert '"audio_sha256"' in metadata
    assert str(ledger.actual_total()) == "0.50"


def test_live_partner_i2v_can_complete_through_webhook(tmp_path):
    app, ledger = setup(tmp_path)
    callback = tmp_path / "i2v-callback.json"

    def transport(req, timeout):
        if req.full_url.startswith("data:video"):
            return None, b"video", {}
        callback.write_text(json.dumps({
            "request_id": "i2v-queued-1",
            "inference_status": {"cost": "0.50", "runtime_ms": 120000},
            "video_url": "data:video/mp4;base64,dmlkZW8=",
        }), encoding="utf-8")
        return 200, json.dumps({
            "request_id": "i2v-queued-1",
            "inference_status": {"status": "queued"},
        }).encode(), {}

    result = app.run_image_video(
        "https://temporary.example/maya.png",
        "Preserve Maya and synchronize her supplied speech.",
        audio_input="https://temporary.example/maya.wav",
        live=True,
        confirmed=True,
        allow_partner=True,
        client=DeepInfraClient("token", transport),
        output_dir=tmp_path,
        webhook_url="https://temporary.example/webhook/current",
        webhook_result_path=callback,
        webhook_wait_seconds=30,
    )
    assert (tmp_path / f"{result.request_id}.mp4").read_bytes() == b"video"
    assert ledger.actual_total() == Decimal("0.50")


def test_partner_avatar_accepts_public_https_without_persisting_url(tmp_path):
    app, ledger = setup(tmp_path)
    result = app.run_avatar(
        "https://temporary.example/portrait.jpg", "Hello", "Kore (Female)",
        gaze_direction="screen_right", allow_partner=True,
    )
    assert result.dry_run is True
    events = ledger.db.execute("SELECT metadata FROM events ORDER BY sequence").fetchall()
    assert all("temporary.example" not in (row[0] or "") for row in events)


def test_partner_avatar_rejects_insecure_image_url_without_reserving(tmp_path):
    app, ledger = setup(tmp_path)
    with pytest.raises(PolicyError, match="public HTTPS"):
        app.run_avatar(
            "http://temporary.example/portrait.jpg", "Hello", "Kore (Female)",
            gaze_direction="screen_right", allow_partner=True,
        )
    assert ledger.reserved_total() == 0


def test_live_partner_avatar_uses_partner_policy_cap_and_persists_video(tmp_path):
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
        gaze_direction="screen_right", live=True, confirmed=True,
        allow_partner=True, client=client, output_dir=tmp_path,
        voice_realization=approved_voice(
            "PrunaAI/p-video-avatar", "Kore (Female)", seed=0,
            voice_language="English (US)",
        ),
    )
    assert result.reserved_usd == app.config.model("lip_sync_avatar").reserve(seconds=8)
    assert (tmp_path / f"{result.request_id}.mp4").read_bytes() == b"video"
    assert str(ledger.actual_total()) == "0.10"
    metadata = ledger.db.execute(
        "SELECT metadata FROM events WHERE event='completed'"
    ).fetchone()[0]
    assert "avatar-provider-1" in metadata
    assert "data:image" not in metadata


def test_partner_avatar_targets_one_speaker_in_a_paired_landscape_plate(tmp_path):
    app, ledger = setup(tmp_path)
    payloads = []
    response = {
        "video_url": "data:video/mp4;base64,dmlkZW8=",
        "request_id": "avatar-provider-paired",
        "inference_status": {"cost": "0.10"},
    }

    def transport(req, timeout):
        if req.full_url.startswith("data:video"):
            return None, b"video", {}
        payloads.append(json.loads(req.data))
        return 200, json.dumps(response).encode(), {}

    app.run_avatar(
        "data:image/png;base64,aW1hZ2U=", "Hello", "Kore (Female)",
        gaze_direction="screen_left", speaker_position="frame_right",
        live=True, confirmed=True, allow_partner=True,
        voice_realization=approved_voice(
            "PrunaAI/p-video-avatar", "Kore (Female)", seed=0,
        ),
        client=DeepInfraClient("token", transport), output_dir=tmp_path,
    )

    prompt = payloads[0]["video_prompt"]
    expected = app.config.model("lip_sync_avatar").data[
        "paired_subject_prompt_template"
    ].format(speaker_side="frame right", listener_side="frame left")
    assert expected in prompt
    metadata = ledger.db.execute(
        "SELECT metadata FROM events WHERE event='completed'"
    ).fetchone()[0]
    assert '"speaker_position": "frame_right"' in metadata


def test_partner_avatar_question_holds_partner_eyeline(tmp_path):
    app, _ = setup(tmp_path)
    payloads = []
    response = {
        "video_url": "data:video/mp4;base64,dmlkZW8=",
        "request_id": "avatar-provider-question",
        "inference_status": {"cost": "0.05"},
    }

    def transport(req, timeout):
        if req.full_url.startswith("data:video"):
            return None, b"video", {}
        payloads.append(json.loads(req.data))
        return 200, json.dumps(response).encode(), {}

    app.run_avatar(
        "data:image/png;base64,aW1hZ2U=", "How much?", "Kore (Female)",
        gaze_direction="screen_right", response_anticipation=True,
        live=True, confirmed=True, allow_partner=True,
        voice_realization=approved_voice(
            "PrunaAI/p-video-avatar", "Kore (Female)", seed=0,
        ),
        client=DeepInfraClient("token", transport), output_dir=tmp_path,
    )

    prompt = payloads[0]["video_prompt"]
    expected = app.config.model("lip_sync_avatar").data[
        "response_anticipation_prompt"
    ].format(gaze_direction="screen right")
    assert expected in prompt


def test_partner_avatar_attempt_cap_is_five(tmp_path):
    app, ledger = setup(tmp_path)
    model = app.config.model("lip_sync_avatar")
    for index in range(5):
        ledger.reserve(f"avatar-{index}", model.id, model.reserve(seconds=8), app.cap)
    with pytest.raises(PolicyError, match="avatar request cap"):
        app.run_avatar(
            "https://temporary.example/portrait.jpg", "Hello", "Kore (Female)",
            gaze_direction="screen_right", allow_partner=True,
        )


def test_partner_avatar_rejects_camera_or_missing_gaze(tmp_path):
    app, ledger = setup(tmp_path)
    with pytest.raises(PolicyError, match="camera gaze is forbidden"):
        app.run_avatar(
            "https://temporary.example/portrait.jpg", "Hello", "Kore (Female)",
            gaze_direction=None, allow_partner=True,
        )
    assert ledger.reserved_total() == 0


def test_explicit_run_and_avatar_attempt_caps_are_enforced(tmp_path):
    ledger = Ledger(tmp_path / "ledger.db")
    app = Orchestrator(ProjectConfig.load(), ledger, "cad_10",
                       run_cap_usd=Decimal("8"), partner_avatar_attempt_cap=8)
    assert app.cap == Decimal("8")
    assert app.partner_avatar_attempt_cap == 8
    with pytest.raises(PolicyError, match="no higher than profile cap"):
        Orchestrator(ProjectConfig.load(), ledger, "cad_10", run_cap_usd=Decimal("10.01"))
