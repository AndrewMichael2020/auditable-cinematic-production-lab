from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
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
            if characters <= 0:
                raise PolicyError("speech reservation requires positive characters")
            return Decimal(str(self.data["price_usd_per_million_characters"])) * characters / 1_000_000
        if "price_usd_per_million_input_tokens" in self.data:
            if input_tokens < 0 or output_tokens < 0 or input_tokens + output_tokens <= 0:
                raise PolicyError("token reservation requires a positive token count")
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
        required = {
            "budget", "approved_models", "execution_policy", "pricing", "proof",
            "provider_policy", "secrets_policy",
        }
        missing = required - raw.keys()
        if missing:
            raise PolicyError(f"project config missing: {', '.join(sorted(missing))}")
        cls._validate_budget(raw["budget"])
        cls._validate_models(raw["approved_models"])
        cls._validate_execution(raw["execution_policy"])
        cls._validate_pricing(raw["pricing"])
        cls._validate_secrets(raw["secrets_policy"])
        return cls(raw)

    @staticmethod
    def _positive_decimal(value: Any, context: str) -> Decimal:
        try:
            number = Decimal(str(value))
        except Exception as exc:
            raise PolicyError(f"{context} must be numeric") from exc
        if not number.is_finite() or number <= 0:
            raise PolicyError(f"{context} must be positive and finite")
        return number

    @classmethod
    def _validate_budget(cls, budget: Any) -> None:
        if not isinstance(budget, dict) or not isinstance(budget.get("profiles"), dict):
            raise PolicyError("budget requires profiles")
        profiles = budget["profiles"]
        default = str(budget.get("default_profile", ""))
        if not profiles or default not in profiles:
            raise PolicyError("budget default_profile must name an existing profile")
        account_limit = cls._positive_decimal(
            budget.get("deepinfra_account_spending_limit_usd_max"),
            "DeepInfra account spending limit",
        )
        for name, profile in profiles.items():
            if not isinstance(profile, dict):
                raise PolicyError(f"budget profile {name} must be an object")
            cap = cls._positive_decimal(
                profile.get("application_hard_cap_usd"), f"budget profile {name} cap"
            )
            if cap > account_limit:
                raise PolicyError(f"budget profile {name} exceeds the provider account limit")
        for field in ("reservation_required_before_request", "reconcile_after_request"):
            if budget.get(field) is not True:
                raise PolicyError(f"budget policy requires {field}=true")

    @classmethod
    def _validate_models(cls, models: Any) -> None:
        if not isinstance(models, dict) or not models:
            raise PolicyError("approved_models must be a non-empty object")
        model_ids: set[str] = set()
        for role, data in models.items():
            if not isinstance(data, dict):
                raise PolicyError(f"approved model {role} must be an object")
            for field in ("id", "endpoint_type", "licence"):
                if not str(data.get(field, "")).strip():
                    raise PolicyError(f"approved model {role} requires {field}")
            model_id = str(data["id"])
            if model_id in model_ids:
                raise PolicyError(f"approved model id is assigned to multiple roles: {model_id}")
            model_ids.add(model_id)
            price_schemes = sum(
                key in data for key in (
                    "price_usd_per_second", "price_usd_per_million_characters",
                    "price_usd_per_million_input_tokens",
                )
            )
            if price_schemes != 1:
                raise PolicyError(f"approved model {role} requires exactly one pricing scheme")
            price_fields = [key for key in data if key.startswith("price_usd_")]
            for field in price_fields:
                cls._positive_decimal(data[field], f"approved model {role} {field}")
            if "price_usd_per_million_input_tokens" in data and \
                    "price_usd_per_million_output_tokens" not in data:
                raise PolicyError(f"approved model {role} requires output token pricing")

    @staticmethod
    def _validate_execution(policy: Any) -> None:
        required_true = {
            "live_run_requires_explicit_flag", "append_only_ledger_required",
            "output_sha256_required", "human_review_required_for_final_acceptance",
        }
        required_false = {
            "recursive_retries_allowed", "provider_self_retry_allowed",
            "automatic_partner_model_fallback_allowed",
            "automatic_retry_after_unknown_billing_status_allowed",
        }
        if not isinstance(policy, dict) or policy.get("default_mode") != "dry_run":
            raise PolicyError("execution policy must default to dry_run")
        if any(policy.get(field) is not True for field in required_true):
            raise PolicyError("execution policy is missing a required fail-closed control")
        if any(policy.get(field) is not False for field in required_false):
            raise PolicyError("execution policy must disable retries and automatic fallbacks")
        if policy.get("paid_request_concurrency") != 1:
            raise PolicyError("paid request concurrency must be exactly one")

    @staticmethod
    def _validate_pricing(pricing: Any) -> None:
        if not isinstance(pricing, dict):
            raise PolicyError("pricing must be an object")
        if pricing.get("fail_if_unverified_or_increased") is not True:
            raise PolicyError("pricing must fail closed")
        if pricing.get("price_refresh_requires_human_approval") is not True:
            raise PolicyError("price refresh must require human approval")
        try:
            date.fromisoformat(str(pricing["verified_at"]))
            max_age = int(pricing["max_age_days"])
        except (KeyError, TypeError, ValueError) as exc:
            raise PolicyError("pricing requires verified_at and positive max_age_days") from exc
        if max_age <= 0:
            raise PolicyError("pricing max_age_days must be positive")

    @staticmethod
    def _validate_secrets(policy: Any) -> None:
        if not isinstance(policy, dict) or policy.get(
            "consumer_session_credentials_must_not_be_stored"
        ) is not True:
            raise PolicyError("secrets policy must forbid stored consumer session credentials")
        required = policy.get("github_actions_required")
        forbidden = policy.get("forbidden")
        if not isinstance(required, list) or not required or not isinstance(forbidden, list):
            raise PolicyError("secrets policy requires explicit required and forbidden lists")
        names = {str(item.get("name", "")) for item in required if isinstance(item, dict)}
        if not names or "" in names or names & {str(item) for item in forbidden}:
            raise PolicyError("required and forbidden credential names must be non-empty and disjoint")

    def require_current_pricing(self, *, as_of: date | None = None) -> None:
        pricing = self.raw["pricing"]
        verified = date.fromisoformat(str(pricing["verified_at"]))
        current = as_of or date.today()
        age = (current - verified).days
        if age < 0 or age > int(pricing["max_age_days"]):
            raise PolicyError(
                f"pricing snapshot from {verified.isoformat()} is stale; human refresh required"
            )

    def profile_cap(self, profile: str) -> Decimal:
        try:
            value = self.raw["budget"]["profiles"][profile]["application_hard_cap_usd"]
        except KeyError as exc:
            raise PolicyError(f"unknown budget profile: {profile}") from exc
        return self._positive_decimal(value, f"budget profile {profile} cap")

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
