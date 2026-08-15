import base64
import json

import pytest

from video_gen.elevenlabs import ElevenLabsClient
from video_gen.errors import ProviderError, UnknownBillingStatus


def test_lists_current_voice_catalog_read_only():
    requests = []

    def transport(req, timeout):
        requests.append((req, timeout))
        return 200, b'{"voices":[{"voice_id":"sarah","name":"Sarah"}]}', {}

    voices = ElevenLabsClient("key", transport=transport).list_voices()
    assert voices == [{"voice_id": "sarah", "name": "Sarah"}]
    assert requests[0][0].method == "GET"
    assert requests[0][0].headers["Xi-api-key"] == "key"


def test_generates_timestamped_dialogue_and_records_credit_header():
    requests = []
    response = {
        "audio_base64": base64.b64encode(b"RIFFaudio").decode(),
        "voice_segments": [{"voice_id": "sarah", "start_time_seconds": 0.0}],
        "alignment": {"characters": ["H"]},
    }

    def transport(req, timeout):
        requests.append((req, timeout))
        return 200, json.dumps(response).encode(), {
            "request-id": "eleven-request-1",
            "character-cost": "42",
        }

    result = ElevenLabsClient("key", transport=transport).text_to_dialogue(
        [{"text": "Hello", "voice_id": "sarah"}], seed=3407
    )
    assert result.audio == b"RIFFaudio"
    assert result.provider_request_id == "eleven-request-1"
    assert result.character_cost == 42
    request = requests[0][0]
    assert request.full_url.endswith("output_format=wav_24000")
    assert json.loads(request.data) == {
        "inputs": [{"text": "Hello", "voice_id": "sarah"}],
        "model_id": "eleven_v3",
        "language_code": "en",
        "seed": 3407,
        "apply_text_normalization": "auto",
    }


def test_dialogue_fails_closed_when_credit_usage_is_unknown():
    response = {
        "audio_base64": base64.b64encode(b"RIFFaudio").decode(),
        "voice_segments": [],
    }

    def transport(req, timeout):
        return 200, json.dumps(response).encode(), {"request-id": "request-1"}

    with pytest.raises(UnknownBillingStatus, match="character-cost"):
        ElevenLabsClient("key", transport=transport).text_to_dialogue(
            [{"text": "Hello", "voice_id": "sarah"}]
        )


def test_generates_one_timestamped_persona_line():
    requests = []
    response = {
        "audio_base64": base64.b64encode(b"RIFFline").decode(),
        "alignment": {"characters": ["H", "i"]},
    }

    def transport(req, timeout):
        requests.append((req, timeout))
        return 200, json.dumps(response).encode(), {
            "request-id": "speech-request-1",
            "character-cost": "17",
        }

    result = ElevenLabsClient("key", transport=transport).text_to_speech(
        "May I see your BC Services Card, please?",
        "sarah/voice",
        seed=3407,
    )
    assert result.audio == b"RIFFline"
    assert result.provider_request_id == "speech-request-1"
    assert result.character_cost == 17
    request = requests[0][0]
    assert "/sarah%2Fvoice/with-timestamps?" in request.full_url
    assert json.loads(request.data)["text"] == (
        "May I see your BC Services Card, please?"
    )


def test_generates_bounded_looping_sound_effect():
    requests = []

    def transport(req, timeout):
        requests.append((req, timeout))
        return 200, b"ID3ambience", {
            "request-id": "sound-request-1",
            "character-cost": "220",
            "content-type": "audio/mpeg",
        }

    result = ElevenLabsClient("key", transport=transport).sound_effect(
        "Quiet outpatient clinic reception chatter.",
        duration_seconds=20,
        loop=True,
        prompt_influence=0.55,
    )
    assert result.audio == b"ID3ambience"
    assert result.character_cost == 220
    assert result.content_type == "audio/mpeg"
    request = requests[0][0]
    assert request.full_url.endswith("output_format=mp3_44100_192")
    assert json.loads(request.data) == {
        "text": "Quiet outpatient clinic reception chatter.",
        "loop": True,
        "prompt_influence": 0.55,
        "model_id": "eleven_text_to_sound_v2",
        "duration_seconds": 20,
    }


def test_sound_effect_rejects_unbounded_duration_before_network():
    with pytest.raises(ProviderError, match="0.5 to 30"):
        ElevenLabsClient("key").sound_effect("Clinic", duration_seconds=31)
