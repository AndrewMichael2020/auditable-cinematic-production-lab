# Artifact strategy

Status: active from 2026-08-15.

The repository keeps proof visible without turning Git into the delivery-media store. This is a
forward-looking policy: it preserves the portfolio evidence already linked from the README and does
not rewrite public history.

## Storage tiers

| Tier | Keep here | Retention and checks |
|---|---|---|
| Git | source, tests, manifests, policies, compact JSON/Markdown decisions, selected contact sheets, and the existing README-linked proof clips | permanent; credential scan and large-artifact guard on every PR |
| GitHub release assets | accepted delivery media, checksums, and a bounded source/evidence bundle | permanent for a named release; SHA-256 published beside each bundle |
| GitHub Actions artifacts | zero-cost build output and explicitly manual smoke-run packets | short-lived; the dry-run bundle uses seven days and the manual smoke packet uses 30 days |
| Local or cold storage | provider downloads, raw takes, lossless audio, intermediates, rejected media, and private references | retained according to production value; hashes and compact decisions remain portable |

## Existing evidence stays

The following README-linked artifacts remain in Git and are grandfathered by
`artifact-policy/legacy-large-files.json`:

- `runs/clinic-stage2-20260803T060048Z/final/clinic-stage2-sequence-v3.mp4`
- `runs/cliffhanger-20260802T235825Z/final-the-call-15s.mp4`

Other existing tracked run evidence is not silently deleted. The policy blocks new or enlarged
tracked files over 5 MiB, and blocks new or modified media under `runs/` in a change set. A deliberate
exception requires a reviewed policy change with the exact path and maximum size.

## Local evidence reviewed on 2026-08-15

The ignored local tree also contains `runs/clinic-cosmos-final-v03/`: a 35.459-second 720p master,
a 3.5 MiB 480p review copy, and compact provenance/QA files. Its machine gate is
`pass_with_human_playback_review_pending`, while promotion remains false. It therefore stays local
until normal-speed review with sound is complete. If accepted later, the review copy or master can
be published as a release asset with its existing SHA-256; it should not be force-added to Git.

## Bounded release bundle

`video-gen-release build` creates a deterministic bundle containing the CLI source, policy,
zero-cost sample, expected output, provider snapshot, and selected JSON/Markdown evidence for the
accepted Stage 2 clinic sequence. It excludes media, databases, archives, credentials, signed URLs,
and local-only files; each member and the bundle itself receive SHA-256 checksums.

The retained proof media remains playable through the README and GitHub release assets. The bounded
bundle provides inspection and reproduction without duplicating those media files.

## Historical Git size

The public history already contains earlier large run artifacts. Removing those objects would need a
history rewrite and force push, with consequences for existing clones and links. No such rewrite is
part of this policy. If repository cloning becomes a material problem, handle that as a separate,
explicitly approved migration after release assets and redirects are verified.
