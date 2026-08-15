# Project instructions

- Use `./scripts/sandbox` for Python execution, tests, FFmpeg checks, and dry-run CLI validation.
- Keep the host checkout read-only during execution. Apply reviewed source edits on the host, then verify them in the disposable sandbox copy.
- Do not mount `.env`, provider credentials, or local model caches into the default sandbox.
- Do not enable runtime network access or live provider flags in the default sandbox.
- Local model inference requires a separate explicit profile with read-only weights, one model resident at a time, and a narrowly scoped writable run directory.
- Keep final edits, provider approvals, paid calls, persistent outputs, and acceptance decisions with the main Codex agent and user.
