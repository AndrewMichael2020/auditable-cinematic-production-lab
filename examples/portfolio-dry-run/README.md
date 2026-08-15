# Zero-cost portfolio sample

This fictional 20-second scene is deliberately small and contains no private source material,
provider output, credentials, or paid dependency. Run it from the repository or release-bundle root:

```bash
video-gen preflight --profile cad_10 \
  --output /tmp/cinematic-preflight.json
diff -u examples/portfolio-dry-run/expected/preflight.json \
  /tmp/cinematic-preflight.json

video-gen validate-scene examples/portfolio-dry-run/scene.json \
  --output /tmp/cinematic-scene-plan.json

video-gen audit-av-sync examples/portfolio-dry-run/av-sync-calibration.json \
  --output /tmp/cinematic-av-sync.json
diff -u examples/portfolio-dry-run/expected/av-sync-calibration-report.json \
  /tmp/cinematic-av-sync.json
```

What this proves:

- the policy configuration loads without credentials or network access;
- a structured scene compiles into four continuity-aware prompts and passes the spatial gate;
- the AV-offset evaluator can resolve an 80 ms target using 20 ms evidence cadence;
- the fixture is labelled `calibration_fixture`, so it cannot be mistaken for proof that a real
  production artifact is synchronized.

No command above contacts a provider. Paid generation still requires a separate manual workflow,
an approved model and price snapshot, reservation capacity, `--live`, and `--confirm-live`.
