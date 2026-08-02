# Secrets and credentials

## Current requirement

No repository secret is required for Stages 0–3.

| Capability | Authentication now | Repository secret |
|---|---|---|
| ChatGPT/Codex planning, coding, reference work, and review | Andrew's interactive ChatGPT subscription | None |
| Gemini/Flow included-credit video generation | Andrew's interactive Google subscription, with manual approval | None |
| GitHub Copilot implementation support | Andrew's GitHub subscription | None |
| Local orchestration, validation, FFmpeg checks, and assembly | Local execution | None |
| GitHub Actions | GitHub supplies GITHUB_TOKEN automatically for each workflow run | Do not create a duplicate secret |

Consumer subscriptions are not API credentials. Do not copy browser cookies, session tokens, OAuth caches, or login exports into GitHub Secrets, repository files, CI variables, or automation code.

The present build can validate schemas, compile prompts, import manually generated media, run local checks, and assemble review packets without provider credentials. Actual Flow generation remains an interactive boundary because the included consumer credits do not provide a safe unattended API or a repository-secret contract.

## Reserved future secret names

These names are documented now so later provider adapters have a stable contract. None is required or permitted under the current zero-spend policy.

| GitHub Actions secret | Future purpose | Present status |
|---|---|---|
| DEEPINFRA_API_TOKEN | Paid DeepInfra video inference adapter | Disabled until paid_api_calls_allowed becomes true and a cash cap is approved |
| OPENAI_API_KEY | Separately billed OpenAI API evaluation or prompt-repair adapter | Disabled; the ChatGPT subscription does not supply this credit |
| ELEVENLABS_API_KEY | ElevenLabs speech adapter | Disabled until the adapter, quota, and spending controls are approved |

The local equivalents appear as blank entries in .env.example. A real .env file remains ignored.

## Deliberately absent Google credentials

Do not create GEMINI_API_KEY, GOOGLE_API_KEY, or GOOGLE_APPLICATION_CREDENTIALS for this proof.

Those credentials would use Gemini API, Vertex AI, or Google Cloud rather than the included Flow consumer-credit workflow. project.json explicitly prohibits those billed paths. If that policy changes later, Google authentication must be designed as a separate provider adapter with a verified project, quota, and hard budget gate.

## When a paid adapter is approved

Only then add the specific secret at:

Settings → Secrets and variables → Actions → New repository secret

Never add all reserved secrets merely because they are listed here. Add only the credential required by the approved adapter. Keep secret values out of commits, logs, ledgers, prompts, screenshots, generated manifests, and issue text.

Any workflow that needs a provider secret must:

1. fail closed when the secret is absent;
2. remain dry-run by default;
3. require an explicit provider-enable flag;
4. enforce the approved budget before sending a request;
5. redact authorization headers and provider responses;
6. forbid unattended or recursive generation retries.

## Important distinction

Building the engine requires no paid-provider secret. Running a future paid provider adapter will require the corresponding secret and a deliberate change to the budget policy.
