# Video Generation Test

A budget-controlled, programmatic experiment toward an AI drama production engine using open-source models hosted by DeepInfra.

## Current goal

Produce one reproducible **12–30 second scene** before building a full engine:

- one location;
- two adult characters;
- four to six necessary shots, including a wide master;
- consistent character descriptions, wardrobe, location, and screen direction;
- credible action, dialogue rhythm, and editing;
- complete cost and provenance records.

The repository contains the Stage 1 golden scene, a 15-second dialogue continuation, and a
live-tested Stage 2 orchestrator. It still
defaults to dry-run mode. A bounded CAD 10 smoke campaign has validated Data URL media persistence,
cost reconciliation, technical inspection, and human candidate selection against DeepInfra.

## Programmatic model stack

The default proof uses one DeepInfra API token and OSS models. A separately gated,
user-approved partner exception exists only for the bounded lip-sync avatar test.

| Stage | DeepInfra model | Licence | Role |
|---|---|---|---|
| Planning | `Qwen/Qwen3-32B` | Apache 2.0 | Structured shot planning and prompt compilation |
| Cheap drafts | `FastVideo/FastWan-QAD-FP8-1.3B` | Apache 2.0 | Many 5-second 480p prompt tests |
| Final candidates | `Wan-AI/Wan2.2-T2V-A14B` | Apache 2.0 | Selected 5-second 720p generations |
| Visual QA | `Qwen/Qwen3-VL-30B-A3B-Instruct` | Apache 2.0 | Contact-sheet scoring and defect labels |
| Dialogue audio | `ResembleAI/chatterbox-turbo` | MIT | Speech generation and expressive timing |
| Lip-sync test | `PrunaAI/p-video-avatar` | Provider metadata unspecified | Explicit partner exception; disabled by default |
| Assembly | FFmpeg | LGPL/GPL by build | Editing, audio mix, and technical validation |

Wan 2.6, Wan 2.7, PixVerse, Veo, Gemini API, Vertex AI, OpenAI API, and ElevenLabs
remain outside the runtime proof. The local ElevenLabs key, when present, is optional and was not used
for the validated clip.

The DeepInfra video endpoint is:

```text
POST https://api.deepinfra.com/v1/inference/{model}
Authorization: Bearer $DEEPINFRA_TOKEN
```

## Cash rule

Choose exactly one run profile: **10, 15, or 20 dollars Canadian**, including a conservative allowance for currency conversion and 12% tax.

| Profile | Application hard cap in US dollars |
|---|---:|
| CAD 10 | US$6.50 |
| CAD 15 | US$9.75 |
| CAD 20 | US$13.00 |

The program must stop before the selected US-dollar cap. It must also respect a DeepInfra account spending limit of no more than US$13.00 for the proof. DeepInfra reports actual cost in `inference_status.cost`; the local append-only ledger records both reserved and reported cost.

Only sequential generation is allowed. Every request reserves its maximum expected cost before transmission. No recursive retries, parallel paid jobs, automatic provider fallback, or unbounded workflow reruns.

At currently listed prices, one 5-second FastWan draft costs US$0.0125 and one 5-second Wan 2.2 final candidate costs US$0.375. A useful 20-second proof with extensive cheap drafts and 12 Wan 2.2 candidates should remain well below the CAD 10 profile.

## Required secret

Create one repository secret:

```text
DEEPINFRA_API_TOKEN
```

For local runs, expose the same value as `DEEPINFRA_TOKEN`. Never commit the token. See [docs/SECRETS.md](docs/SECRETS.md).

ChatGPT/Codex and GitHub Copilot subscriptions may be used to develop and review the repository, but the production workflow does not pretend they are API credits. Gemini is not used.

## Intended workflow

1. Validate the selected CAD budget profile and reserve expected cost.
2. Compile structured shot prompts with Qwen.
3. Generate cheap FastWan drafts.
4. Run FFmpeg checks and Qwen-VL contact-sheet review.
5. Human-select prompts worth promoting.
6. Generate bounded Wan 2.2 final candidates.
7. Generate dialogue audio with Chatterbox.
8. Assemble 12–30 seconds with FFmpeg and produce a manifest containing every model, prompt, seed, cost, output hash, and decision.
9. Stop automatically when the budget, candidate, or retry limit is reached.

Human approval remains required before promoting drafts to the more expensive final model and before final acceptance. The execution itself is programmatic.

## Run locally

The core has no runtime Python dependencies and supports Python 3.11 or later. Install the CLI and
test dependency, then validate the complete dry-run path:

```bash
python -m pip install -e . pytest
pytest -q
video-gen preflight --profile cad_10
video-gen validate-scene
video-gen audit-scene --output runs/storyboard-spatial-audit.json
video-gen plan-video --profile cad_10 --role draft_video \
  --prompt "A locked wide shot on the rainy platform" --seed 101
```

`plan-video` reserves the maximum expected charge in the local append-only SQLite ledger but does
not contact DeepInfra. A paid request additionally requires both `--live` and `--confirm-live`, plus
`DEEPINFRA_TOKEN` in the process environment. Final-model requests use the same confirmation as the
human-promotion gate. Successful outputs are downloaded atomically, hashed, and recorded with the
provider request ID and reported cost. Unknown billing status is terminal and is never retried.

Generated ledgers and media live under ignored `runs/` and `outputs/` directories. Inspect and
human-approve the four compiled prompts from `scenes/golden-scene.json` before any live draft run.

The spatial gate runs before generation and checks platform/track geometry, safe blocking, object
support, wardrobe construction, scale, continuity anchors, unwanted text, sparse environmental
symbolism, a required wide master, and explicit interlocutor eyelines. Every planned gaze has a
screen direction and a fail-closed `camera_look_forbidden` flag. `audit-draft` then combines explicit
contact-sheet observations with FFprobe facts. A failed or uncertain criterion blocks promotion.

The optional partner lip-sync path requires `--allow-partner-avatar`, `--live`, and
`--confirm-live` for each sequential speaker request. `plan-avatar` also requires a screen-left or
screen-right gaze. `prepare-dialogue` applies bounded trims, a single picture-and-audio rate change,
and a crop without breaking synchronization. `assemble-scene` joins a 2–5 second wide master and
three to five already-synchronized turns, normalizes dialogue to an EBU R128 target, pads only the
final dramatic beat, and emits an output hash manifest. It never activates automatically.

The bounded 15-second continuation in `scenes/platform-cliffhanger.json` used four dialogue turns
and one rejected gaze-calibration take. Its five sequential partner attempts cost US$0.55 actual
against US$1.00 reserved. The final output is 1280×720 with stereo audio; ElevenLabs was not needed.
The ignored run folder retains raw source takes, edit masters, compact actor references, a cost
ledger, manifests, per-shot defect evidence, final QA, and the final contact sheet.

Use `audit-artifacts` before cleanup. `prune-artifacts` is a dry run unless `--apply` is supplied and
only removes previews, sampled-frame sheets, and other deterministic derivatives. It retains raw and
final media, ledgers, manifests, reports, hashes, and compact references fail-closed.

The repository workflows are manual-dispatch only; development pushes and pull requests do not
start generation. If a human later chooses to run **live DeepInfra smoke test** and enters `LIVE`,
the workflow makes exactly one FastWan request (maximum reserved
cost US$0.0125), never retries it, and retains the generated clip, append-only SQLite ledger,
compiled prompt, command result, hashes, and JSON audit export as a workflow artifact for 30 days.
Signed query parameters from provider output URLs are deliberately excluded from the ledger.

## Repository map

- [docs/PLAN.md](docs/PLAN.md): staged architecture and proof plan.
- [docs/LESSONS-AND-NEXT-STEPS.md](docs/LESSONS-AND-NEXT-STEPS.md): live-run lessons, reusable guardrails, and Pareto next steps.
- [docs/SECRETS.md](docs/SECRETS.md): exact authentication and spending-control contract.
- [.env.example](.env.example): local variable names without values.
- [project.json](project.json): machine-readable models, budgets, and stop conditions.
- [scenes/golden-scene.json](scenes/golden-scene.json): one-location, two-character, four-shot proof.
- [scenes/platform-cliffhanger.json](scenes/platform-cliffhanger.json): 15-second master-plus-dialogue continuation.
- [`src/video_gen`](src/video_gen): CLI, policy, ledger, provider, production, and media modules.
- [`tests`](tests): fail-closed budget, provider, scene, and orchestration tests.
- [LICENSE](LICENSE): repository licence.

No full episode, autonomous open-ended retry loop, or foundation-model training is in scope yet.
