# Secrets and credentials

## Required provider secret

The programmatic proof requires exactly one user-created GitHub Actions secret:

```text
DEEPINFRA_API_TOKEN
```

It authenticates the approved DeepInfra planning, cinematic generation, visual-review, and speech models.

Add it at:

```text
Repository Settings → Secrets and variables → Actions → New repository secret
```

Do not put the value in an issue, pull request, commit, workflow input, project manifest, generated ledger, screenshot, or log.

## Local variable

Local code reads:

```text
DEEPINFRA_TOKEN
```

A GitHub Actions workflow maps the repository secret to that variable:

```yaml
env:
  DEEPINFRA_TOKEN: ${{ secrets.DEEPINFRA_API_TOKEN }}
```

The real local `.env` file remains ignored. [.env.example](../.env.example) contains only blank variable names.

## Optional local dialogue provider

`ELEVENLABS_KEY` may exist in the ignored local `.env`. It is read only by `match-voices` and an
explicitly confirmed `plan-dialogue-candidate --live --confirm-live` call. It must never be copied to
GitHub Actions, manifests, ledgers, screenshots, or logs. Catalog matching is read-only; dialogue
generation records the provider request ID and credit usage but never the key.

## Not required

Do not create these secrets for the initial proof:

- `OPENAI_API_KEY`;
- `GEMINI_API_KEY`;
- `GOOGLE_API_KEY`;
- `GOOGLE_APPLICATION_CREDENTIALS`.

Gemini partner models may be used through DeepInfra with the same `DEEPINFRA_TOKEN`, explicit model
registration, and normal budget reservation. Direct Gemini/Flow or Vertex credentials and billing,
OpenAI API, and unregistered media providers are excluded. ElevenLabs is limited to the registered
voice-catalog and dialogue-candidate operations above. ChatGPT/Codex and GitHub Copilot can support
repository development interactively, but are not part of runtime authentication.

GitHub supplies `GITHUB_TOKEN` automatically for each Actions run. Do not create a duplicate repository secret.

## DeepInfra account control

Before the first live run:

1. Add a payment method or prepaid balance as required by DeepInfra.
2. Set the DeepInfra account spending limit to no more than **US$13.00** for this proof.
3. Select a lower application profile when appropriate:
   - CAD 10 → US$6.50;
   - CAD 15 → US$9.75;
   - CAD 20 → US$13.00.
4. Confirm the token belongs to the intended DeepInfra account.
5. Run the repository's future preflight command in dry-run mode.
6. Enable live generation only for the approved run.

The account limit is a second guard. The application ledger and reservation logic remain mandatory.

## Workflow requirements

Any workflow that can access `DEEPINFRA_API_TOKEN` must:

1. fail closed if the secret is absent;
2. use dry-run by default;
3. require an explicit budget profile;
4. permit only models in the approved OSS registry;
5. reserve maximum expected cost before each request;
6. run one paid request at a time;
7. record DeepInfra's reported `inference_status.cost`;
8. redact authorization headers and token-shaped values;
9. prohibit recursive retries and automatic partner-model fallback;
10. avoid running on pull requests from forks;
11. use the least GitHub permissions required;
12. never upload the token inside an artifact or cache.

A timeout with unknown billing status blocks automatic retry until the request is reconciled.

## Rotation

Rotate either provider key immediately if it appears in a commit, log, artifact, issue, pull request,
screenshot, or copied terminal output. Removing exposed text does not make the old key safe.
