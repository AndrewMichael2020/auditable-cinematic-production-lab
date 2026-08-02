from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from .config import ProjectConfig
from .errors import PolicyError, UnknownBillingStatus
from .ledger import Ledger
from .provider import DeepInfraClient, prompt_hash


@dataclass(frozen=True)
class PlannedRequest:
    request_id: str
    model: str
    reserved_usd: Decimal
    prompt_sha256: str
    dry_run: bool


class Orchestrator:
    def __init__(self, config: ProjectConfig, ledger: Ledger, profile: str):
        self.config = config
        self.ledger = ledger
        self.profile = profile
        self.cap = config.profile_cap(profile)

    def run_video(self, role: str, prompt: str, *, seconds: int = 5, seed: int = 0,
                  live: bool = False, confirmed: bool = False,
                  client: DeepInfraClient | None = None,
                  output_dir: str | Path = "outputs") -> PlannedRequest:
        if role not in {"draft_video", "final_video"}:
            raise PolicyError("run_video accepts approved video roles only")
        if role == "final_video" and live and not confirmed:
            raise PolicyError("final generation requires explicit human promotion")
        if live and not confirmed:
            raise PolicyError("live request requires --confirm-live")
        model = self.config.model(role)
        profile_data = self.config.raw["budget"]["profiles"][self.profile]
        count_key = "max_fastwan_5s_drafts" if role == "draft_video" else "max_wan22_5s_finals"
        if self.ledger.reservation_count(model.id) >= int(profile_data[count_key]):
            raise PolicyError(f"candidate cap reached for {role}")
        configured_seconds = int(model.data["seconds"])
        if seconds != configured_seconds:
            raise PolicyError(f"{model.id} is approved for exactly {configured_seconds} seconds")
        payload = {"prompt": prompt, "duration": seconds, "seed": seed}
        reserved = model.reserve(seconds=seconds)
        request_id = str(uuid.uuid4())
        self.ledger.reserve(request_id, model.id, reserved, self.cap)
        planned = PlannedRequest(request_id, model.id, reserved, prompt_hash(payload), not live)
        if not live:
            return planned
        if client is None:
            client = DeepInfraClient(os.environ.get("DEEPINFRA_TOKEN", ""))
        try:
            result = client.infer(model.id, payload)
        except UnknownBillingStatus:
            self.ledger.append(request_id, "billing_unknown")
            raise
        except Exception:
            self.ledger.append(request_id, "failed")
            raise
        if result.cost > reserved:
            self.ledger.append(request_id, "billing_unknown", actual=result.cost)
            raise UnknownBillingStatus("reported cost exceeded approved reservation")
        destination = Path(output_dir) / f"{request_id}.mp4"
        try:
            output_sha256 = client.download(result.output_url, str(destination))
        except Exception:
            self.ledger.append(request_id, "failed", actual=result.cost,
                               metadata=json.dumps({"reason": "download_failed"}))
            raise
        metadata = json.dumps({"provider_request_id": result.provider_request_id,
                               "output_url": result.output_url, "output_path": str(destination),
                               "output_sha256": output_sha256,
                               "prompt_sha256": planned.prompt_sha256}, sort_keys=True)
        self.ledger.append(request_id, "completed", actual=result.cost, metadata=metadata)
        return planned
