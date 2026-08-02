from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from .errors import PolicyError


@dataclass(frozen=True)
class Model:
    role: str
    id: str
    endpoint_type: str
    licence: str
    data: dict[str, Any]

    def reserve(self, *, seconds: int = 0, input_tokens: int = 0,
                output_tokens: int = 0, characters: int = 0) -> Decimal:
        if "price_usd_per_second" in self.data:
            if seconds <= 0:
                raise PolicyError("video reservation requires positive seconds")
            return Decimal(str(self.data["price_usd_per_second"])) * seconds
        if "price_usd_per_million_characters" in self.data:
            return Decimal(str(self.data["price_usd_per_million_characters"])) * characters / 1_000_000
        if "price_usd_per_million_input_tokens" in self.data:
            incoming = Decimal(str(self.data["price_usd_per_million_input_tokens"])) * input_tokens
            outgoing = Decimal(str(self.data["price_usd_per_million_output_tokens"])) * output_tokens
            return (incoming + outgoing) / 1_000_000
        raise PolicyError(f"unknown reservation price for {self.id}")


@dataclass(frozen=True)
class ProjectConfig:
    raw: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path = "project.json") -> "ProjectConfig":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        required = {"budget", "approved_models", "execution_policy", "proof"}
        missing = required - raw.keys()
        if missing:
            raise PolicyError(f"project config missing: {', '.join(sorted(missing))}")
        if raw.get("pricing", {}).get("fail_if_unverified_or_increased") is not True:
            raise PolicyError("pricing must fail closed")
        return cls(raw)

    def profile_cap(self, profile: str) -> Decimal:
        try:
            value = self.raw["budget"]["profiles"][profile]["application_hard_cap_usd"]
        except KeyError as exc:
            raise PolicyError(f"unknown budget profile: {profile}") from exc
        return Decimal(str(value))

    def model(self, role: str) -> Model:
        try:
            data = self.raw["approved_models"][role]
        except KeyError as exc:
            raise PolicyError(f"model role not approved: {role}") from exc
        return Model(role, data["id"], data["endpoint_type"], data["licence"], data)

    def require_model(self, model_id: str) -> Model:
        for role in self.raw["approved_models"]:
            model = self.model(role)
            if model.id == model_id:
                return model
        raise PolicyError(f"model is not approved: {model_id}")

