# Video Generation Test

A budget-controlled experiment toward a programmatic, provider-independent AI drama production engine.

## Current goal

Prove the hardest production risks in one **15–30 second scene** before building a full engine:

- one location;
- two adult characters;
- four planned shots;
- consistent faces, wardrobe, location, and screen direction;
- credible acting and dialogue rhythm;
- a coherent final edit.

This repository is currently in the **planning and experiment-design phase**. It contains no provider integrations and triggers no paid generation.

## Cost rule

The initial incremental budget is **0 dollars Canadian**.

Existing subscriptions may be used only through their included consumer interfaces:

- ChatGPT/Codex: planning, coding, reference-image work, and review;
- Gemini/Flow: manually approved video generations using included credits only;
- GitHub Copilot: optional implementation support, not video generation.

A subscription is not assumed to include API credit. Gemini API, Vertex AI, Google Cloud billing, automatic credit reload, and paid retries are disabled for the initial proof.

Before every video generation, record the displayed credit cost and balance. Stop if the interface requests a purchase, upgrade, billing activation, or additional credits.

## Secrets right now

**None.** Stages 0–3 require no repository secret.

ChatGPT/Codex, Gemini/Flow, and GitHub Copilot subscriptions are interactive entitlements, not API keys. Do not store browser sessions or consumer-login credentials. Flow generation remains manually approved.

Future provider secret names and their activation rules are defined in [docs/SECRETS.md](docs/SECRETS.md). The blank [.env.example](.env.example) is a contract for future adapters, not a request to add credentials now.

## Why this repository exists

The durable product will be the orchestration and evidence layer, not a permanent dependency on one model. It should eventually own:

- scripts, scenes, shots, characters, wardrobe, locations, and continuity constraints;
- reference assets and prompt versions;
- provider requests, seeds, outputs, costs, and provenance;
- technical checks, visual evaluation, bounded retries, and human approval;
- final assembly and an evidence trail for every accepted shot.

## Repository map

- [docs/PLAN.md](docs/PLAN.md): staged implementation and experiment plan.
- [docs/SECRETS.md](docs/SECRETS.md): exact credential contract and safety rules.
- [.env.example](.env.example): blank future-provider variable names.
- [project.json](project.json): machine-readable constraints and stop conditions.
- [LICENSE](LICENSE): MIT licence.

## Current workflow

1. Design the golden scene and acceptance rubric at no incremental cost.
2. Verify subscription balances and that automatic reload is inactive.
3. Generate candidates manually in Flow within the recorded included-credit cap.
4. Save every output and its provenance.
5. Assemble and evaluate the scene.
6. Decide whether the evidence justifies writing the first orchestrator.

No full episode, autonomous paid retry loop, or foundation-model training is in scope yet.
