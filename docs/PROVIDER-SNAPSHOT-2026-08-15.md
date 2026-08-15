# Provider and pricing snapshot — 2026-08-15

This snapshot separates current, provider-published capabilities from historical or planned lanes.
It confirms configuration metadata; it does not authorize a paid request. Live execution still
requires a registered role, reservation capacity, a current price that has not increased, provider
credentials, `--live`, and `--confirm-live`.

## Verified current runtime entries

| Registered role | Provider model or service | Provider-published price on 2026-08-15 | Runtime status |
|---|---|---:|---|
| Planning | [`Qwen/Qwen3-32B`](https://deepinfra.com/Qwen/Qwen3-32B/api) | US$0.08 input / US$0.28 output per 1M tokens | Registered historical planning lane |
| Visual QA | [`Qwen/Qwen3-VL-30B-A3B-Instruct`](https://deepinfra.com/Qwen/Qwen3-VL-30B-A3B-Instruct/api) | US$0.15 input / US$0.60 output per 1M tokens | Registered contact-sheet evaluator |
| Final candidate | [`Wan-AI/Wan2.2-T2V-A14B`](https://deepinfra.com/Wan-AI/Wan2.2-T2V-A14B/api) | US$0.075 per second | Registered at five seconds and 720p |
| Physics-aware candidate | [`nvidia/Cosmos3-Super`](https://deepinfra.com/nvidia/Cosmos3-Super/api) | US$0.05 per second at 720p | Registered only after storyboard authorization and promotion/repair approval |
| Audio-conditioned dialogue | [`Wan-AI/Wan2.6-I2V`](https://deepinfra.com/Wan-AI/Wan2.6-I2V/api) | US$0.10 per second | Partner exception; disabled by default and individually bounded |
| Canonical voice design | [`Qwen/Qwen3-TTS`](https://deepinfra.com/Qwen/Qwen3-TTS/api) | US$20 per 1M characters | Versioned realization plus approved audition hash required before motion |
| Basic speech proof | [`ResembleAI/chatterbox-turbo`](https://deepinfra.com/ResembleAI/chatterbox-turbo/api) | US$1 per 1M characters | Non-canonical speech testing only |
| Lip-sync experiment | [`PrunaAI/p-video-avatar`](https://deepinfra.com/PrunaAI/p-video-avatar/api) | US$0.025 per second | Partner exception; disabled by default and capped per request |
| Multi-speaker dialogue | [`ElevenLabs text-to-dialogue with timestamps`](https://elevenlabs.io/docs/api-reference/text-to-dialogue/convert-with-timestamps) | Provider credits, not converted to an invented USD rate | Human casting and exact-performance review required |

The DeepInfra model pages above were checked directly on the snapshot date. The machine registry in
`project.json` pins the same base rates and fails live execution if the snapshot is older than 30 days
or a current price is higher than the reservation basis. ElevenLabs usage stays in native reported
credits because plan-specific credit economics are not equivalent to a stable per-character USD rate.

## Historical or constrained, not the current creative promise

- Wan 2.6 I2V and p-video-avatar are partner-model exceptions. Neither is an automatic fallback.
- The accepted Stage 2 evidence records what actually ran; this snapshot does not retroactively
  replace model, cost, or acceptance provenance.

## Planned or unverified options

The Stage 3 plan discusses an OpenAI creative-reasoning lane, local Apple Silicon video candidates,
additional DeepInfra evaluators, and possible NVIDIA-hosted routes. Those are research candidates,
not executable runtime entries. They remain blocked until their exact model IDs, provider routes,
terms, prices, request bounds, fixed evaluation results, and human approval are recorded.

## Refresh procedure

1. Open each official provider page and compare model ID, availability, unit, and base price.
2. If a configured price increased or a unit changed, leave live generation blocked and revise the
   reservation basis only after human review.
3. Update this dated snapshot and `pricing.verified_at` together.
4. Run the credential-free CI path. Do not exercise a paid endpoint as part of the refresh.
