# Implementation plan

## Decision

Build this project programmatically, but in evidence-gated stages. The first deliverable is not a large application. It is a reproducible one-location proof and the structured production record needed to learn from it.

Consumer subscriptions are useful for development and manual generation. They do not provide a safe basis for unattended production APIs. Until a provider exposes a verified hard spending cap with no overage path, generation remains a human-approved boundary.

## Constraints

| Constraint | Rule |
|---|---|
| Initial incremental spend | 0 dollars Canadian |
| Location | One |
| Characters | Two adults |
| Finished duration | 15–30 seconds |
| Planned shots | Four |
| Initial candidates | Up to three per shot |
| Corrective candidates | Up to two across the scene |
| Included Gemini/Flow credits | Lower of 200 credits or 20% of the displayed monthly balance |
| Paid APIs | Disabled |
| Automatic reload | Must be inactive |
| Retry behavior | Bounded; never recursive or unattended |
| Human review | Required before generation, fallback, and final acceptance |

The credit ceiling overrides the candidate counts. Reaching the credit ceiling ends generation even if fewer candidates exist.

## Target architecture

The eventual engine should separate six concerns:

1. **Production model**: story, episode, scene, shot, character, wardrobe, location, and continuity state.
2. **Asset registry**: immutable references, generated media, hashes, versions, and provenance.
3. **Provider adapters**: replaceable interfaces for image, video, speech, and lip-sync providers.
4. **Evaluation**: deterministic media checks, reference similarity, model-assisted review, and human judgment.
5. **Control plane**: budget reservation, bounded retry policy, approval gates, and resumable run state.
6. **Assembly**: edit decisions, audio mix, captions, encoding, and final manifest.

Provider adapters must never own story or continuity truth. The production record remains authoritative.

## Stage 0 — Repository foundation

Status: **complete when these planning files are committed**.

Deliverables:

- concise project scope;
- implementation plan;
- machine-readable budget and experiment constraints;
- exclusions for credentials and generated media.

No provider SDK or application framework is selected yet.

## Stage 1 — Golden-scene design

Incremental cost: **0 dollars Canadian**.

Create:

- a 15–30 second script with one emotional turn;
- character cards with stable physical, wardrobe, voice, and behavior constraints;
- one location card with layout, lighting, time, and camera-axis rules;
- four shot records with duration, framing, action, dialogue, continuity inputs, and acceptance criteria;
- a review rubric scored per shot and across the assembled scene.

The design should be provider-neutral. Prompts are compiled from the structured records rather than treated as the source of truth.

Exit gate:

- every shot is necessary;
- continuity constraints are explicit;
- the scene can be evaluated without subjective guesswork alone.

## Stage 2 — Included-credit proof

Incremental cost: **0 dollars Canadian**.

Preflight before each manual generation:

1. Confirm automatic credit reload is inactive.
2. Confirm no Google Cloud or Vertex AI billing path is being used.
3. Record timestamp, displayed balance, displayed generation cost, model/mode, shot ID, and prompt version.
4. Confirm the projected balance remains within the experiment credit ceiling.
5. Generate only after human approval.
6. Record the resulting balance and output identifier.

Stop immediately on:

- any purchase, upgrade, billing, or insufficient-credit prompt;
- missing or ambiguous displayed cost;
- automatic reload appearing active;
- projected credit use above the ceiling;
- 12 initial candidates, two corrective candidates, or the global credit ceiling;
- repeated identity or continuity defects that indicate the design must change.

Exit gate:

- one assembled 15–30 second scene;
- complete credit and provenance ledger;
- per-shot and scene-level evaluation;
- measured accepted-seconds ratio and retry count;
- a written decision to stop, redesign, or proceed.

## Stage 3 — Minimal local orchestrator

Start only after Stage 2 produces useful evidence.

Implement the smallest local tool that can:

- validate project, scene, shot, character, location, and ledger records;
- allocate stable IDs and content hashes;
- compile prompts from approved structured inputs;
- import manually generated outputs;
- run local media checks with FFmpeg;
- create contact sheets and review packets;
- calculate credit/cost totals and enforce stop conditions;
- resume from append-only run state.

Default behavior must be offline and dry-run. Network adapters remain disabled unless explicitly enabled.

Initial implementation preference:

- Python 3.11+;
- Pydantic or JSON Schema for contracts;
- SQLite for durable local state;
- FFmpeg/ffprobe for deterministic media inspection;
- pytest for policy and state-transition tests.

This is a preference, not a locked decision. The evidence from Stage 2 can change it.

## Stage 4 — Provider adapters

Add one adapter at a time only when it has:

- documented API terms and commercial-use rights;
- explicit pricing and a verifiable spending-control strategy;
- idempotency or safe request tracking;
- timeouts, transient-error classification, and bounded retries;
- complete request/response provenance;
- a provider-independent output contract.

A provider is never allowed to trigger its own retry.

## Retry policy

For a rejected shot:

1. Retry a transient transport/provider failure with the same request.
2. Try one new seed without changing production constraints.
3. Apply one conservative prompt repair.
4. Route to an approved alternative provider only after human authorization.
5. Stop for redesign or human judgment.

Every attempt is retained as labelled evidence. No recursive retry implementation is permitted.

## Evaluation order

1. Technical validity: decode, duration, aspect ratio, resolution, blank frames, freezes, blur, and audio integrity.
2. Reference checks: character, wardrobe, location, and key composition constraints.
3. Model-assisted review: sampled frames or contact sheets for anatomy, identity, continuity, and intended action.
4. Human review: acting, emotional effect, dialogue rhythm, edit quality, and final acceptance.

A language or vision model cannot be the sole acceptance authority.

## Deferred decisions

These should not be fixed until the golden-scene evidence exists:

- primary video provider;
- automated lip-sync provider;
- web UI or dashboard framework;
- cloud storage;
- distributed queues;
- autonomous model routing;
- fine-tuning;
- a full 10–12 minute episode.

## Definition of success

The proof succeeds if it establishes, with complete provenance:

- acceptable identity and environment continuity across four edited shots;
- understandable action and emotional change;
- credible enough dialogue timing for the intended format;
- a reproducible cost per accepted second;
- clear evidence about which failure classes automation can reduce.

A visually attractive isolated clip without continuity, provenance, or cost evidence does not satisfy the experiment.
