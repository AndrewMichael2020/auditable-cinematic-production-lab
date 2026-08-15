# Reproducibility record

Release target: v0.2.0. Updated 2026-08-15.

The public GitHub Actions workflow executes the repository on clean Ubuntu runners with Python 3.11
and 3.12, no provider credential, no network inference, and no `--live` flag. This is an externally
executed environment check, not a third-party creative endorsement or adoption claim.

## Reproduction contract

From a clean checkout:

```bash
python -m pip install -e . pytest
video-gen-secret-scan
pytest -q
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
video-gen-release build
video-gen-release verify dist/cinematic-production-lab-v0.2.0.zip
```

From the extracted v0.2.0 release bundle, the smaller public contract is self-contained:

```bash
python -m pip install -e .
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
video-gen-release build --output /tmp/rebuilt-v0.2.0.zip
video-gen-release verify /tmp/rebuilt-v0.2.0.zip
```

All commands in both paths are zero-cost. The sample is fictional and contains no provider output,
credential, private reference, or local dependency. The full test suite remains a clean-checkout and
GitHub Actions contract; the release bundle intentionally excludes test-only fixtures and media.

## What each check establishes

| Check | Evidence | Does not establish |
|---|---|---|
| Tracked credential scan | no supported credential signature in tracked text | absence of every possible secret class |
| Unit tests on 3.11/3.12 | policy, ledger, provider, editing, voice, AV-sync, retention, and release behavior | visual quality of a generated film |
| Scene validation | structured scene, blocking, eyeline, continuity, privacy, and prompt compilation | provider output quality |
| AV calibration | 20 ms evidence cadence can evaluate the configured ±80 ms boundary | lip sync of any production artifact |
| Release verification | member hashes, deterministic bundle, no media/database/archive member, credential scan | third-party adoption |
| Manual normal-speed review | perceptual acceptance with sound on ordinary playback | an objective timestamp measurement by itself |

## Accepted, rejected, and pending evidence

- Accepted: the Stage 2 clinic sequence remains linked in the README with its run report, manifest,
  costs, hashes, observations, and acceptance decision.
- Accepted continuation: the 15-second dialogue continuation remains linked with its compact proof
  records.
- Rejected: the ad-hoc full clinic expansion remains explicitly rejected for voice mismatch and
  perceptible lip asynchrony; it is not promoted by passing transport or ASR checks.
- Pending: the local v03 clinic repair has an automated gate pass but still requires normal-speed
  audiovisual review and is not a promoted portfolio artifact.

## Independent review still welcome

The GitHub-hosted CI run is reproducibility evidence from a clean external environment. A genuine
independent filmmaking review, downstream adoption example, or published user evaluation remains a
separate and valuable next validation artifact.
