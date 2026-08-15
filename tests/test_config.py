import json
from datetime import date
from decimal import Decimal

import pytest

from video_gen.config import ProjectConfig
from video_gen.errors import PolicyError


def test_registry_and_costs():
    config = ProjectConfig.load()
    assert config.profile_cap("cad_10") == Decimal("10.0")
    assert config.model("draft_video").reserve(seconds=5) == Decimal("0.0125")
    assert config.model("final_video").reserve(seconds=5) == Decimal("0.375")
    assert config.model("lip_sync_avatar").reserve(seconds=8) == Decimal("0.200")


def test_unknown_profile_and_model_fail_closed():
    config = ProjectConfig.load()
    with pytest.raises(PolicyError):
        config.profile_cap("unlimited")
    with pytest.raises(PolicyError):
        config.require_model("partner/expensive")


def test_invalid_costs_and_units_fail_closed():
    config = ProjectConfig.load()
    with pytest.raises(PolicyError, match="positive characters"):
        config.model("speech").reserve(characters=0)
    with pytest.raises(PolicyError, match="positive token count"):
        config.model("planning").reserve(input_tokens=-1)


def test_live_pricing_snapshot_expires_without_human_refresh():
    config = ProjectConfig.load()
    config.require_current_pricing(as_of=date(2026, 9, 2))
    with pytest.raises(PolicyError, match="stale"):
        config.require_current_pricing(as_of=date(2026, 9, 3))


def test_config_rejects_unsafe_execution_policy(tmp_path):
    raw = ProjectConfig.load().raw
    mutated = json.loads(json.dumps(raw))
    mutated["execution_policy"]["recursive_retries_allowed"] = True
    path = tmp_path / "project.json"
    path.write_text(json.dumps(mutated), encoding="utf-8")
    with pytest.raises(PolicyError, match="disable retries"):
        ProjectConfig.load(path)
