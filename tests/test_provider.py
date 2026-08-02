import json
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
    client = DeepInfraClient("x", lambda request, timeout: (_ for _ in ()).throw(TimeoutError()))
    with pytest.raises(UnknownBillingStatus):
        client.infer("m", {})


def test_http_failure_is_safe():
    client = DeepInfraClient("x", lambda request, timeout: (401, b'secret details', {}))
    with pytest.raises(ProviderError, match="401"):
        client.infer("m", {})

