import json
import hashlib
import http.client
from decimal import Decimal

import pytest

from video_gen.errors import ProviderError, UnknownBillingStatus
from video_gen.provider import DeepInfraClient, redact


def test_parses_cost_and_output_without_leaking_token():
    def transport(request, timeout):
        assert request.get_header("Authorization", "").startswith("Bearer ")
        return 200, json.dumps({"video_url": "https://example/video.mp4", "inference_status": {"cost": 0.0125}}).encode(), {"x-request-id": "p1"}
    result = DeepInfraClient("secret-value", transport).infer("approved/model", {"prompt": "hello"})
    assert result.cost == Decimal("0.0125")
    assert result.provider_request_id == "p1"
    assert redact("Authorization: Bearer secret-value") == "Authorization: Bearer [REDACTED]"


def test_missing_cost_and_timeout_block_retry():
    client = DeepInfraClient("x", lambda request, timeout: (200, b'{"video_url":"x"}', {}))
    with pytest.raises(UnknownBillingStatus):
        client.infer("m", {})
    client = DeepInfraClient(
        "x",
        lambda request, timeout: (_ for _ in ()).throw(
            http.client.RemoteDisconnected("closed")
        ),
    )
    with pytest.raises(UnknownBillingStatus, match="connection closed"):
        client.infer("m", {})


def test_submits_and_parses_documented_webhook_envelope():
    calls = []

    def transport(request, timeout):
        calls.append(json.loads(request.data))
        return 200, json.dumps({
            "request_id": "queued-1",
            "inference_status": {"status": "queued"},
        }).encode(), {}

    client = DeepInfraClient("x", transport)
    queued = client.submit_webhook(
        "nvidia/Cosmos3-Super",
        {"prompt": "locked clinic"},
        "https://example.test/webhook/token",
    )
    assert queued.provider_request_id == "queued-1"
    assert calls == [{
        "prompt": "locked clinic",
        "webhook": "https://example.test/webhook/token",
    }]
    completed = client.result_from_webhook({"prompt": "locked clinic"}, {
        "request_id": "queued-1",
        "inference_status": {"status": "succeeded", "cost": "0.25"},
        "results": {"video": "data:video/mp4;base64,dmlkZW8="},
    })
    assert completed.cost == Decimal("0.25")
    assert completed.output_url.startswith("data:video/mp4")


def test_parses_native_top_level_video_webhook_without_status_field():
    packet = {
        "request_id": "cosmos-native-1",
        "inference_status": {"cost": 0.249996, "runtime_ms": 183284},
        "video_url": "data:video/mp4;base64,dmlkZW8=",
    }
    result = DeepInfraClient("x").result_from_webhook({}, packet)
    assert result.provider_request_id == "cosmos-native-1"
    assert result.cost == Decimal("0.249996")
    assert result.output_url == packet["video_url"]
    client = DeepInfraClient("x", lambda request, timeout: (_ for _ in ()).throw(TimeoutError()))
    with pytest.raises(UnknownBillingStatus):
        client.infer("m", {})


def test_missing_inline_cost_is_reconciled_once_by_request_id():
    calls = []

    def transport(request, timeout):
        calls.append(request.full_url)
        if request.full_url.endswith("/v1/request-costs"):
            assert json.loads(request.data) == {"requestIds": ["voice-1"]}
            return 200, json.dumps({
                "requests": [{"requestId": "voice-1", "costNanoUsd": 5_000_000}]
            }).encode(), {}
        return 200, json.dumps({
            "request_id": "voice-1", "audio": "UklGRg=="
        }).encode(), {}

    result = DeepInfraClient("x", transport).infer_audio(
        "Qwen/Qwen3-TTS-VoiceDesign",
        {"input": "hello", "response_format": "wav"},
    )
    assert result.provider_request_id == "voice-1"
    assert result.cost == Decimal("0.005")
    assert result.output_url == "data:audio/wav;base64,UklGRg=="
    assert calls == [
        "https://api.deepinfra.com/v1/inference/Qwen/Qwen3-TTS-VoiceDesign",
        "https://api.deepinfra.com/v1/request-costs",
    ]


def test_audio_cost_can_use_exact_provider_character_count_and_verified_rate():
    body = {
        "request_id": "voice-2",
        "audio": "UklGRg==",
        "input_character_length": 5,
    }
    client = DeepInfraClient(
        "x", lambda request, timeout: (200, json.dumps(body).encode(), {})
    )
    result = client.infer_audio(
        "Qwen/Qwen3-TTS",
        {"input": "hello", "response_format": "wav"},
        fallback_price_usd_per_million_characters=Decimal("20"),
    )
    assert result.cost == Decimal("0.0001")
    assert result.raw["_cost_source"] == (
        "provider_input_character_length_x_verified_registry_rate"
    )


def test_audio_character_cost_fallback_rejects_usage_mismatch():
    body = {
        "request_id": "voice-3",
        "audio": "UklGRg==",
        "input_character_length": 4,
    }
    client = DeepInfraClient(
        "x", lambda request, timeout: (200, json.dumps(body).encode(), {})
    )
    with pytest.raises(UnknownBillingStatus, match="did not match"):
        client.infer_audio(
            "Qwen/Qwen3-TTS",
            {"input": "hello", "response_format": "wav"},
            fallback_price_usd_per_million_characters=Decimal("20"),
        )


def test_http_failure_is_safe():
    client = DeepInfraClient("x", lambda request, timeout: (401, b'secret details', {}))
    with pytest.raises(ProviderError, match="401"):
        client.infer("m", {})


def test_parses_documented_video_field():
    body = {"video": "data:video/mp4;base64,dmlkZW8=", "inference_status": {"cost": 0}}
    client = DeepInfraClient("x", lambda request, timeout: (200, json.dumps(body).encode(), {}))
    assert client.infer("m", {}).output_url == body["video"]


def test_download_accepts_video_data_url(tmp_path):
    destination = tmp_path / "clip.mp4"
    digest = DeepInfraClient("x").download(
        "data:video/mp4;base64,dmlkZW8=", str(destination)
    )
    assert destination.read_bytes() == b"video"
    assert digest == hashlib.sha256(b"video").hexdigest()


def test_audio_inference_normalizes_base64_output():
    body = {"audio": "UklGRg==", "words": [], "inference_status": {"cost": "0.000004"}}
    client = DeepInfraClient("x", lambda request, timeout: (200, json.dumps(body).encode(), {}))
    result = client.infer_audio("m", {"text": "test", "response_format": "wav"})
    assert result.output_url == "data:audio/wav;base64,UklGRg=="
    assert result.cost == Decimal("0.000004")
