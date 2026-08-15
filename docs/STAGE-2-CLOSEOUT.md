# Stage 2 closeout: from generated clips to a production system

Date: 2026-08-04
Status: strategic closeout with declared carry-forward debt

## Decision

Stage 2 is closed as an evidence-rich prototype stage. Its strict exit gate required two contrasting
sequences to pass every hard gate; that did not happen. One earlier clinic baseline was accepted, and
the Maya/Kenji v03 sequence is the strongest shareability candidate, but v03 still has a transient
card-surface blip, a handoff that plays too slowly, no living wide establishing coverage, and a
pending normal-speed human audiovisual acceptance decision.

At the user's direction, those defects will not trigger another clinic repair cycle. They become
named entry debt for Stage 3. This is preferable to implying that the defects vanished or spending
repeatedly on one scene after its major architectural lessons are already clear.

This closeout should not obscure the achievement. Stage 2 produced roughly one minute of coherent,
concluded two-character dialogue in a beautifully rendered clinic environment, with persona-bound
voices and realistic multi-voice clinic ambience. It moved the work from attractive isolated clips
to an end-to-end authored conversation with production lineage, bounded spend and a traceable final
assembly. The remaining card, motion and coverage defects define the next craft frontier; they do
not erase that advance.

## Evidence reviewed

The closeout covers the progression from the rejected visual-only-persona clinic run through:

- the series-owned Maya and Kenji visual and voice personas;
- Sarah and Bill as immutable, auditioned ElevenLabs realizations;
- one sequence-wide timestamped dialogue performance and exact ASR-derived turn boundaries;
- Wan audio-conditioned single-speaker performances;
- Cosmos face-free spatial/action inserts;
- typed setup, take, clip, shot, cut and transition lineage;
- deterministic exact-content repair for the BC Services Card;
- multi-voice clinic ambience, loudness normalization and final ASR;
- bounded paid attempts, provider receipts, hashes, conservative unknown-cost reservations and
  isolated tests;
- v03's 35.459-second 720p master and 480p review copy.

The v03 automated audit is
`runs/clinic-cosmos-final-v03/audits/final-v03-audit.json`. Its automated gate passes, while its human
playback gate remains intentionally pending.

## Capability progression

| Capability | Earlier failure | Stage 2 result | Carry-forward requirement |
|---|---|---|---|
| Character continuity | Run-local faces and ad hoc voices | Series-owned personas, reference packs and voice lineage | Preserve the same realization across scenes and episodes |
| Dialogue | Correct words but wrong voice and weak sync evidence | Persona-bound performance master, Wan synchronized picture, ASR-derived edits | Add human and objective utterance-level sync evidence |
| Visual world | Attractive but inconsistent clinic clips | Strong shared clinic identity, colour and workstation geography | Build living wides and return-to-master coverage |
| Physical action | Ambiguous or blank card handoff | Cosmos preserves one-card ownership and transfer | Control action tempo and exact surface stability separately |
| Exact content | Generated model invented or simplified a required card | Official-layout fictional `SAMPLE` prop with deterministic source pixels | Track exact surface pixels through motion instead of regenerating them |
| Sound | Bare room tone or white-noise-like hum | Spatialized multi-voice background activity beneath dialogue | Add synchronized foley and perform ordinary-speaker listening review |
| Editing | Clip duration controlled scene rhythm | Speech-window trimming, motivated audio lead and typed timeline | Lock rhythm in an animatic before generation and use broader coverage |
| Cost and provenance | Generation was the unit of success | Accepted seconds, hashes, receipts, reservations and bounded repairs | Optimize cost per accepted second and time to accepted sequence |
| Acceptance | Technical success was confused with artistic success | Automated evidence and human acceptance are separate gates | Retain human aesthetic authority and blind comparative review |

## What now works

### Production personas

A character is no longer a face prompt. The series owns appearance, behaviour, voice persona,
provider realization, audition, performance direction and immutable lineage. A lower-level request
cannot silently recast the character.

### Model specialization

The engine no longer assumes one model should solve a complete scene. Wan is useful for visible,
audio-conditioned single-speaker performance. Cosmos is useful for face-free spatial and physical
action. ElevenLabs supplies deliberate persona performances and background ensemble speech. Local
FFmpeg assembly and deterministic compositing preserve exact content and editorial control.

### Fail-closed evidence

ASR proves content, hashes prove transport, contact sheets reveal visual state, and waveform tests
measure audio handling. None is mislabeled as proof of voice identity, acting quality or perceptual
lip sync. Paid attempts are bounded, and unresolved billing remains reserved.

### Editorial salvage

The engine can select useful source intervals, place off-screen dialogue over motivated inserts and
remove silent visible articulation without regenerating every take. This is genuine film editing,
not merely concatenation.

## Remaining defects and root causes

| Debt | Observable defect | Root cause | Stage 3 response |
|---|---|---|---|
| `debt-wide-coverage` | No wide establishing or master shot in v03 | A static plate was rejected, but no living replacement was designed before dialogue generation | Require an animated geography master and at least one later master return in the animatic |
| `debt-action-tempo` | Card handoff feels slow | The prompt described action states but not the intended onset, contact and release timecodes | Add an action clock with target frame/time windows and reject slow motion before assembly |
| `debt-exact-prop-motion` | Brief card-surface blip | A generative video model was still asked to preserve high-information printed pixels during deformation and occlusion | Generate motion and composite/track exact prop pixels as separate layers |
| `debt-perceptual-acceptance` | Final voice, ambience and sync acceptance is not recorded | Automated inspection cannot hear or judge the complete normal-speed experience | Require named human review on headphones and ordinary speakers |
| `debt-local-video-runtime` | Local video generation is not benchmarked on the target Mac | Cloud generation preceded a measured one-model-resident Apple Silicon lane | Benchmark a local video runtime before making it the production baseline |

## Lessons that generalize

1. **Film grammar matters more than isolated clip beauty.** A persuasive close-up cannot replace
   geography, master coverage, reactions, inserts and motivated returns to wider space.
2. **A wide must be alive.** A still anchor is a reference or animatic frame, not finished coverage.
   Establishing shots need purposeful blocking, environmental motion or a motivated camera move.
3. **Physical action is temporal blocking.** Initiation, contact, release and completion require
   target timecodes, not merely prose descriptions of the four states.
4. **Exact surfaces are not generative responsibilities.** Identity cards, screens, labels, legal
   text and recurring logos must use deterministic source pixels, tracking and occlusion masks.
5. **Generate for the edit.** Lock beat duration and intended cut points in an animatic; request
   handles and complementary coverage rather than asking a provider to determine scene rhythm.
6. **Performance continuity starts in sound.** One persona-owned performance master per speaker
   gives the sequence a coherent dramatic arc and stable voice before motion exists.
7. **Atmosphere is semantic and spatial.** A believable room contains distant human activity,
   acoustical perspective, synchronized foley and silence with intention—not broadband noise.
8. **Low budget comes from reuse and selection.** Reusable locations, personas, performance masters,
   reference packs and accepted setup recipes reduce spend more reliably than cheaper weak drafts.
9. **Model routing should follow shot risk.** Dialogue, physical contact, exact props, environment,
   camera motion and post-production are different jobs with different failure modes.
10. **Human review is the artistic authority.** Automated gates prevent avoidable failures; they do
    not decide whether a performance, cut, composition or sound mix feels emotionally true.

## Stage transition

Stage 3 is **Cinematic Grammar and Versatile Series Production**. Its north star is the narrative
economy and repeatability of short-form drama combined with the authored composition, performance,
sound and emotional restraint expected from prestige streaming drama. It translates austere
European naturalism into concrete craft—available light, observational camera placement, spare
production design, uncomfortable emotional proximity and performance over spectacle—rather than
putting a filmmaker's name into executable prompts.

The detailed plan is in [STAGE-3-CINEMATIC-SERIES-PLAN.md](STAGE-3-CINEMATIC-SERIES-PLAN.md).
