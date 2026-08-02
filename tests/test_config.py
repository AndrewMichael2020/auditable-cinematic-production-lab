from decimal import Decimal

import pytest

from video_gen.config import ProjectConfig
from video_gen.errors import PolicyError


def test_registry_and_costs():
    config = ProjectConfig.load()
    assert config.profile_cap("cad_10") == Decimal("6.5")
    assert config.model("draft_video").reserve(seconds=5) == Decimal("0.0125")
    assert config.model("final_video").reserve(seconds=5) == Decimal("0.375")
    assert config.model("lip_sync_avatar").reserve(seconds=8) == Decimal("0.200")


def test_unknown_profile_and_model_fail_closed():
    config = ProjectConfig.load()
    with pytest.raises(PolicyError):
        config.profile_cap("unlimited")
    with pytest.raises(PolicyError):
        config.require_model("partner/expensive")
