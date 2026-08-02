# Implementation plan

## Decision

Use DeepInfra as the single inference provider for the first proof. All selected runtime models have publicly available weights and permissive licences. Gemini/Flow, Vertex AI, OpenAI API, ElevenLabs, and proprietary DeepInfra partner video models are excluded.

The first deliverable is a reproducible one-location scene and its evidence trail, not a large application.

## Constraints

| Constraint | Rule |
|---|---|
| Incremental cash profile | 10, 15, or 20 dollars Canadian |
| Absolute experiment ceiling | 20 dollars Canadian |
| DeepInfra application cap | US$6.50, US$9.75, or US$13.00 |
| Location | One |
| Characters | Two adults |
| Finished duration | 15–30 seconds |
| Planned shots | Four 5-second shots initially |
| Provider | DeepInfra only |
| Runtime models | OSS models in the approved registry only |
| Concurrency | One paid request at a time |
| Retry behavior | Bounded, iterative, and budget-reserved |
| Human review | Required before final-model promotion and final acceptance |
| Gemini/Google billing | Prohibited |
| OpenAI API billing | Prohibited |

The US-dollar caps conservatively assume 1 USD = 1.37 CAD and 12% tax. Before a real run, use the lower of the configured cap and the amount that remains under the DeepInfra account spending limit.

## Approved model registry

| Capability | Model | Licence | Listed price used for reservation |
|---|---|---|---:|
| Planning and prompt compilation | `Qwen/Qwen3-32B` | Apache 2.0 | US$0.08 input / US$0.28 output per 1M tokens |
| Draft text-to-video | `FastVideo/FastWan-QAD-FP8-1.3B` | Apache 2.0 | US$0.0025/second |
| Final text-to-video | `Wan-AI/Wan2.2-T2V-A14B` | Apache 2.0 | US$0.075/second |
| Frame/contact-sheet QA | `Qwen/Qwen3-VL-30B-A3B-Instruct` | Apache 2.0 | US$0.15 input / US$0.60 output per 1M tokens |
| Dialogue audio | `ResembleAI/chatterbox-turbo` | MIT | US$1.00 per 1M characters |

Model names and prices are configuration data. A live run must fail closed if DeepInfra no longer exposes the exact model, the price is unknown, or the configured reservation price is lower than the currently verified price.

## Honest limitation

The two approved video models are text-to-video. They do not provide the reference-conditioned identity control of a strong image-to-video or reference-to-video model.

Therefore, this proof tests how far structured prompts, one controlled location, shot design, selection, and editing can push continuity. It must not claim solved face identity or lip-sync. Dialogue can be placed over reaction shots, profiles, over-the-shoulder compositions, or off-screen beats so the first experiment evaluates drama and editing without pretending visible speech is synchronized.

If continuity remains inadequate, the result is useful evidence. The engine remains provider-independent so a later permissively licensed I2V/R2V adapter can replace the video stage when one is available within budget.

## Target architecture

The eventual engine separates:

1. **Production model**: scene, shot, character, wardrobe, location, dialogue, and continuity state.
2. **Model registry**: exact model IDs, licences, capabilities, prices, and verification dates.
3. **Budget controller**: profile selection, pre-request reservation, actual-cost reconciliation, and hard stops.
4. **DeepInfra adapter**: authenticated requests, response parsing, download, hashes, and provenance.
5. **Evaluation**: FFmpeg checks, contact sheets, Qwen-VL labels, and human decisions.
6. **Run state**: append-only attempts, resumability, and idempotent request records.
7. **Assembly**: selected shots, dialogue audio, edit decisions, encoding, and final manifest.

The provider adapter never owns story or continuity truth. Structured production records remain authoritative.

## Budget controller

Each request follows this order:

1. Resolve model and maximum billable units from the approved registry.
2. Calculate a conservative reservation in US dollars.
3. Reject the request if reserved total plus the new reservation exceeds the selected profile.
4. Append a pending ledger entry with a stable request ID.
5. Send exactly one DeepInfra request.
6. Record HTTP status, provider request ID, model, prompt hash, seed, output URL, and `inference_status.cost`.
7. Reconcile reserved cost to reported cost without ever increasing the remaining cap beyond the original reservation until a human starts a new run.
8. Download the output, calculate SHA-256, and mark the attempt complete or failed.

A timeout with unknown provider status is not retried automatically. It is held for reconciliation so the same paid request is not duplicated.

Recommended proof envelopes:

| CAD profile | FastWan draft ceiling | Wan 2.2 final ceiling | Intended use |
|---|---:|---:|---|
| 10 | 40 × 5 seconds | 12 × 5 seconds | Default complete 20-second proof |
| 15 | 80 × 5 seconds | 20 × 5 seconds | More prompt exploration |
| 20 | 120 × 5 seconds | 28 × 5 seconds | Larger comparison set |

The monetary cap overrides the count ceilings. Planning, QA, and TTS share the same cap.

## Stage 0 — Correct architecture

Status: complete when the repository describes the DeepInfra OSS route, one secret, and CAD caps.

Deliverables:

- approved model registry;
- cost profiles;
- secret contract;
- exclusions for credentials and generated media;
- no actual generation.

## Stage 1 — Golden-scene design

Status: implemented in `scenes/golden-scene.json`.

Cost: negligible DeepInfra text inference, or zero incremental cost when authored through the existing ChatGPT/Codex subscription.

Create:

- a 15–30 second script with one emotional turn;
- two character cards;
- one location card with layout, light, time, and camera-axis rules;
- four shot records;
- dialogue audio plan that does not depend on unverified visible lip-sync;
- per-shot and assembled-scene acceptance criteria.

Exit gate:

- every shot is necessary;
- repeated prompt constraints are explicit;
- the scene is evaluable with objective and human criteria.

## Stage 2 — Minimal orchestrator

Status: implemented as a dependency-light Python CLI with automated fail-closed tests. Live inference
remains intentionally gated and has been validated with bounded draft and promoted-final requests.

Implement only:

- JSON Schema or Pydantic contracts;
- approved model registry;
- DeepInfra HTTP client;
- append-only JSONL or SQLite ledger;
- cost reservation and hard-stop logic;
- sequential draft/final generation commands;
- FFmpeg/ffprobe validation;
- contact-sheet creation;
- Qwen-VL QA;
- Chatterbox audio generation;
- deterministic final assembly.

Default behavior is dry-run. A live command requires the token, a selected budget profile, and explicit confirmation.

Implementation preference:

- Python 3.11+;
- standard HTTP client;
- Pydantic;
- SQLite;
- FFmpeg/ffprobe;
- pytest.

## Stage 3 — Dry-run validation

Status: implemented. The test suite covers registry rejection, conservative reservations, hard caps,
duplicate IDs, missing cost, timeouts, HTTP failures, credential redaction, human promotion, output
download hashing, and malformed production records.

Before any billed request:

- validate all manifests;
- simulate every request and cost;
- verify the chosen profile stops at the correct boundary;
- test missing-secret, higher-price, timeout, duplicate-run, failed-download, and unknown-cost paths;
- verify logs redact authorization headers;
- verify no generated media or local ledger is committed.

Exit gate: all budget and fail-closed tests pass.

## Stage 4 — Live CAD 10 proof

1. Set the DeepInfra account spending limit no higher than US$13 for the whole experiment.
2. Select the CAD 10 application profile.
3. Run cheap draft generations sequentially.
4. Validate and score each draft.
5. Human-approve only selected prompts for Wan 2.2.
6. Generate bounded final candidates.
7. Generate dialogue audio.
8. Assemble and review the 15–30 second scene.
9. Export the complete manifest and cost report.

The CAD 15 and CAD 20 profiles are used only if the CAD 10 evidence justifies a new run.

## Retry policy

For a rejected or failed shot:

1. Reconcile whether the original request was billed.
2. Retry one confirmed transient failure with the same request only if budget is available.
3. Try one new seed.
4. Apply one conservative prompt repair.
5. Stop for human redesign.

No provider self-retry, recursive retry, automatic upgrade to a partner model, or parallel retry is permitted.

## Evaluation order

1. Technical validity: decoding, duration, aspect ratio, resolution, blank frames, freezes, blur, and audio integrity.
2. Structured checks: intended framing, number of people, location elements, wardrobe descriptors, screen direction, and action.
3. Qwen-VL review of sampled frames/contact sheets.
4. Human review of acting, continuity, emotional effect, dialogue rhythm, and edit quality.

A model is never the sole acceptance authority.

## Definition of success

The proof succeeds if it produces:

- one coherent 15–30 second scene in one location;
- a measurable continuity result rather than an unsupported claim;
- a complete prompt, seed, model, cost, and hash trail;
- a reproducible cost per accepted second;
- clear evidence about whether DeepInfra-hosted OSS text-to-video is sufficient for the next stage.
