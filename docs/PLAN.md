# Implementation plan

## Decision

Use DeepInfra as the single inference gateway for the Stage 1 and Stage 2 proofs. The default registry remains
open-weight and permissively licensed. One user-approved, CLI-gated exception permits
`PrunaAI/p-video-avatar` for a bounded two-speaker lip-sync test; provider metadata does not report
its licence. Gemini partner models may be selected through the existing DeepInfra gateway when the
exact model, current provider price, intended role, reservation, and provenance are declared. Direct
Google Gemini/Flow billing, Vertex AI, and OpenAI API remain excluded from the Stage 1/2 runtime.
ElevenLabs is
registered only for read-only dynamic voice shortlisting and explicitly confirmed timestamped
dialogue candidates; neither path authorizes motion generation or automatic casting.

Stage 3 adds a separately benchmarked local video lane, `gpt-5.6-sol` as the planned primary creative
reasoning model, and bounded remote specialist shots. OpenAI API authentication remains a deferred
readiness gate until the user exposes a key; this plan authorizes neither credential handling nor a
paid request. DeepInfra remains an optional secondary reasoning/evaluation provider and a remote
media gateway. The objective is one reproducible 5–12+ minute, multi-set ensemble episode with
interwoven A/B/C plots, not an unsupported claim of premium-series parity.

## Stage 2 closeout and Stage 3 transition

The visual-only-persona clinic run remains rejected because the patient voice and visible dialogue
failed human review. The later Maya/Kenji pipeline repaired the architecture with series-owned voice
personas, one performance master, Wan visible dialogue, Cosmos spatial action and deterministic
exact-content handling. V03 is the strongest review candidate, but it carries a brief card blip,
slow handoff motion, no living wide coverage and pending final human playback acceptance.

Stage 2 is strategically closed at the user's direction rather than repaired indefinitely. Its
strict two-contrasting-sequence exit gate was not met. The known defects are retained as explicit
Stage 3 entry debt in [STAGE-2-CLOSEOUT.md](STAGE-2-CLOSEOUT.md).

No new paid or local motion request is authorized by this plan. Stage 3 first requires:

1. every speaker resolves to one series-owned persona version and immutable voice realization;
2. the voice realization records provider/model/voice version, language and performance direction;
3. a short rendered audition is retained with SHA-256 and human approval for perceived age, timbre,
   gender presentation, accent, diction, pace and dramatic fit;
4. every dialogue line carries character ID, persona version, voice-realization ID and audition hash;
5. visible utterances pass normal-speed review with sound, timecoded closure/plosive checks and an
   objective offset/confidence result when a suitable local tool is available;
6. a perceptual voice mismatch, persistent lead/lag, speech on a still mouth or mouth motion during
   silence fails closed before assembly;
7. a locked animatic, living-wide setup, coverage matrix and timecoded action plan;
8. a separate provenance, licence, disk and memory review before any local video-model installation;
9. a dated official-source scan and fixed-packet evaluation of current frontier reasoning and
   multimodal candidates at stage start, the mid-stage gate and closeout;
10. a project manifest that prevents personas, locations, style rules and continuity state from
    leaking between unrelated productions.

The M5 Pro changes the compute environment, not these gates. Secrets remain outside Git;
ignored run assets are copied separately and hash-verified; tests and dry preflight run before any
model is loaded. Hardware readiness never implies generation approval.

## Stage 1 and Stage 2 constraints

| Constraint                  | Rule                                                       |
| --------------------------- | ---------------------------------------------------------- |
| Incremental cash profile    | 10, 15, or 20 dollars Canadian                             |
| Absolute experiment ceiling | 30 dollars Canadian                                        |
| DeepInfra application cap   | US$6.50, US$9.75, or US$13.00                              |
| Location                    | One                                                        |
| Characters                  | Two adults                                                 |
| Finished duration           | 12–30 seconds; live continuation target 12–15 seconds      |
| Planned shots               | Four to six shots with at least one wide master            |
| Provider                    | DeepInfra only                                             |
| Runtime models              | OSS models in the approved registry only                   |
| Concurrency                 | One paid request at a time                                 |
| Retry behavior              | Bounded, iterative, and budget-reserved                    |
| Human review                | Required before final-model promotion and final acceptance |
| Gemini through DeepInfra    | Allowed only as a declared, budget-reserved partner model  |
| Direct Google/Vertex billing| Prohibited                                                 |
| OpenAI API billing          | Prohibited                                                 |

The US-dollar caps conservatively assume 1 USD = 1.37 CAD and 12% tax. Before a real run, use the lower of the configured cap and the amount that remains under the DeepInfra account spending limit.

## Stage 1 and Stage 2 approved model registry

| Capability                      | Model                            | Licence                  |            Listed price used for reservation |
| ------------------------------- | -------------------------------- | ------------------------ | -------------------------------------------: |
| Planning and prompt compilation | `Qwen/Qwen3-32B`                 | Apache 2.0               | US$0.08 input / US$0.28 output per 1M tokens |
| Non-cinematic staging/cartoon draft only | `FastVideo/FastWan-QAD-FP8-1.3B` | Apache 2.0 | US$0.0025/second |
| Final text-to-video             | `Wan-AI/Wan2.2-T2V-A14B`         | Apache 2.0               |                              US$0.075/second |
| Frame/contact-sheet QA          | `Qwen/Qwen3-VL-30B-A3B-Instruct` | Apache 2.0               | US$0.15 input / US$0.60 output per 1M tokens |
| Dialogue audio                  | `ResembleAI/chatterbox-turbo`    | MIT                      |                    US$1.00 per 1M characters |
| Explicit lip-sync exception     | `PrunaAI/p-video-avatar`         | Not reported by provider |            US$0.025/second reservation basis |
| Bounded Stage 2 image-to-video  | `Wan-AI/Wan2.6-I2V`             | Not reported by provider |                       US$0.10/second at 720P |

Model names and prices are configuration data. A live run must fail closed if DeepInfra no longer exposes the exact model, the price is unknown, or the configured reservation price is lower than the currently verified price.

`FastVideo/FastWan-QAD-FP8-1.3B` is permanently quarantined from Stage 2 cinematic production.
The style evidenced by `shot05-draft-v2-contact.png` is suitable only for explicitly labelled,
disposable non-cinematic staging or cartoon experiments. Its output may never be used as an
aesthetic reference, accepted generation source, persona reference, avatar/lip-sync input,
promotion candidate, edit interval or final media for the series. The Stage 2 audit requires the
generation model ID on every interval and blocks this model even if its container and aspect ratio
are technically valid.

## Honest limitation

The two default video models are text-to-video. They do not provide the reference-conditioned
identity control of a strong image-to-video or reference-to-video model.

Therefore, the main proof tests how far structured prompts, one controlled location, shot design,
selection, and editing can push continuity. It must not claim solved face identity. The separate
partner test may claim visible synchronized speech only for its generated close-up clips; it does
not by itself prove wide-shot continuity or objective SyncNet accuracy.

If continuity remains inadequate, the result is useful evidence. The engine remains provider-independent so a later permissively licensed I2V/R2V adapter can replace the video stage when one is available within budget.

## Target architecture

The eventual engine separates:

1. **Production model**: series, season, episode, sequence, scene, beat, setup, take, clip, source
   interval, shot, cut, transition, canonical persona, episode character state, wardrobe, location,
   dialogue and continuity state.
2. **Model registry**: exact model IDs, licences, capabilities, prices, and verification dates.
3. **Budget controller**: profile selection, pre-request reservation, actual-cost reconciliation, and hard stops.
4. **DeepInfra adapter**: authenticated requests, response parsing, download, hashes, and provenance.
5. **Evaluation**: FFmpeg checks, contact sheets, Qwen-VL labels, and human decisions.
6. **Run state**: append-only attempts, resumability, and idempotent request records.
7. **Assembly**: selected shots, dialogue audio, edit decisions, encoding, and final manifest.

The provider adapter never owns story or continuity truth. Structured production records remain authoritative.

`docs/PRODUCTION-VOCABULARY.md` is the normative vocabulary for generation and editing. New Stage 2
plans, filenames, manifests and audits must use its definitions and typed identifiers. In
particular, a series contains seasons, a season contains episodes, an episode contains sequences, and
a sequence may contain multiple scenes. A scene is one primary time and place; a setup is the
camera/lighting/blocking plan; a take is one uninterrupted attempt; a clip is media; a shot is the
continuous edited image between cuts; and a cut is the exact transition point.

## Budget controller

Each request follows this order:

1. Resolve model and maximum billable units from the approved registry.
2. Calculate a conservative reservation in US dollars.
3. Reject the request if reserved total plus the new reservation exceeds the selected profile.
4. Append a pending ledger entry with a stable request ID.
5. Send exactly one DeepInfra request.
6. Record HTTP status, provider request ID, model, prompt hash, seed, output URL, and `inference_status.cost`.
7. Reconcile reserved cost to reported cost without ever increasing the remaining cap beyond the original reservation until a human starts a new run.
8. Download the output, calculate SHA-256, and mark the attempt complete or failed.

A timeout with unknown provider status is not retried automatically. It is held for reconciliation so the same paid request is not duplicated.

Recommended proof envelopes:

| CAD profile | FastWan draft ceiling | Wan 2.2 final ceiling | Intended use                     |
| ----------- | --------------------: | --------------------: | -------------------------------- |
| 10          |        40 × 5 seconds |        12 × 5 seconds | Default complete 20-second proof |
| 15          |        80 × 5 seconds |        20 × 5 seconds | More prompt exploration          |
| 20          |       120 × 5 seconds |        28 × 5 seconds | Larger comparison set            |

The monetary cap overrides the count ceilings. Planning, QA, and TTS share the same cap.

## Foundation milestone 0 — Correct architecture

Status: complete when the repository describes the DeepInfra OSS route, one secret, and CAD caps.

Deliverables:

- approved model registry;
- cost profiles;
- secret contract;
- exclusions for credentials and generated media;
- no actual generation.

## Foundation milestone 1 — Golden-scene design

Status: implemented in `scenes/golden-scene.json`.

Cost: negligible DeepInfra text inference, or zero incremental cost when authored through the existing ChatGPT/Codex subscription.

Create:

- a 12–30 second script with one emotional turn;
- two character cards;
- one location card with layout, light, time, and camera-axis rules;
- four shot records;
- dialogue audio plan that does not depend on unverified visible lip-sync;
- per-shot and assembled-scene acceptance criteria.
- an early spatial audit covering platform geometry, safe blocking, object support, anatomy/contact,
  wardrobe construction, scale, continuity, unwanted text, and sparse environmental metaphors.
- an explicit gaze map for every character in every shot, with a named interlocutor target, stable
  screen direction, and direct camera gaze forbidden.
- one wide master that proves geography before close coverage.

Exit gate:

- every shot is necessary;
- repeated prompt constraints are explicit;
- the scene is evaluable with objective and human criteria.

## Foundation milestone 2 — Minimal orchestrator

Status: implemented as a dependency-light Python CLI with automated fail-closed tests. Live inference
remains intentionally gated and has been validated with bounded draft and promoted-final requests.

Implement only:

- JSON Schema or Pydantic contracts;
- approved model registry;
- DeepInfra HTTP client;
- append-only JSONL or SQLite ledger;
- cost reservation and hard-stop logic;
- sequential draft/final generation commands;
- FFmpeg/ffprobe validation;
- contact-sheet creation;
- Qwen-VL QA;
- Chatterbox audio generation and an explicit partner-avatar exception for visible speech;
- deterministic final assembly.

Default behavior is dry-run. A live command requires the token, a selected budget profile, and explicit confirmation.

Implementation preference:

- Python 3.11+;
- standard HTTP client;
- Pydantic;
- SQLite;
- FFmpeg/ffprobe;
- pytest.

## Foundation milestone 3 — Dry-run validation

Status: implemented. The test suite covers registry rejection, conservative reservations, hard caps,
duplicate IDs, missing cost, timeouts, HTTP failures, credential redaction, human promotion, output
download hashing, and malformed production records.

Before any billed request:

- validate all manifests;
- simulate every request and cost;
- verify the chosen profile stops at the correct boundary;
- test missing-secret, higher-price, timeout, duplicate-run, failed-download, and unknown-cost paths;
- verify logs redact authorization headers;
- verify no generated media or local ledger is committed.

Exit gate: all budget and fail-closed tests pass.

## Foundation milestone 4 — Live CAD 10 proof

1. Set the DeepInfra account spending limit no higher than US$13 for the whole experiment.
2. Select the CAD 10 application profile.
3. Run cheap draft generations sequentially.
4. Validate and score each draft.
5. Human-approve only selected prompts for Wan 2.2.
6. Generate bounded final candidates.
7. Generate dialogue audio.
8. Assemble and review the 12–30 second scene.
9. Export the complete manifest and cost report.

For local development, persist raw paid outputs and the append-only ledger, then retain only the
minimal useful evidence set: final/source media, compact references, manifests, final contact sheet,
QA decisions, hashes, model metadata, and cost provenance. Intermediate previews and sampled-frame
sheets are deterministic and may be pruned after the final audit report exists.

The CAD 15 and CAD 20 profiles are used only if the CAD 10 evidence justifies a new run.

## Program Stage 2 — Cinematic robustness test runs

Status: strategically closed 2026-08-04 with declared carry-forward debt. Stage 1 proved that the bounded pipeline, billing controls, provenance, basic
continuity and visible synchronized dialogue can work. Stage 2 tests whether the same workflow can
reliably produce short scenes that look and sound like landscape television or film, not merely
technically valid generated video.

The clinic run in `runs/clinic-20260803T011736Z/` is useful Stage 2 baseline evidence, but it does
not pass this gate. Its final container is 1280×720, yet nine accepted avatar sources are 768×1152
portrait. Including the reaction derived from one of those sources, 38.873 of 49.686 final seconds
(78.2%) came from portrait material that was cropped or side-filled into landscape. The final also
contains accidental face cuts and weak composition, hides mouths needed to judge lip sync and has
visible sync drift where mouths can be seen, differs materially from the supplied Surrey clinic
reference, and does not make the patient's BC Care Card handoff clear. Its separately controlled
nurse and patient character references were useful, but they are run-level records rather than
series-owned, versioned personas and do not define or verify Surrey-representative cultural and
voice profiles. Ambience is also effectively inaudible in the opening and ending. Previous
geography, privacy, identity and technical-container passes remain valid within their narrower
scope; they are not cinematic acceptance.

### Cinematic intent

Stage 2 targets high-production-value narrative cinema, not glossy advertising, a corporate
promotional video, beauty imagery or generic stock coverage. Composition, colour, light, duration
and camera distance must be motivated by character, spatial understanding and dramatic change.
For this series, use rigorous but unobtrusive framing, natural practical light, unvarnished human
texture, behaviorally specific restrained acting, and the deliberate turquoise/pale-neutral/
light-wood colour design carried by the clinic reference. “Cinematic” is not a shallow lens-effect
synonym: excessive blur, glamour lighting, plastic skin, presenter smiles and product-display sheen
are blocking aesthetic failures even when the image is technically polished.

Capture this intent once in the series manifest as structured `cinematic_intent`, inherit it into
every sequence prompt, and evaluate it within the cinematic-composition gate. A run may cite films
or filmmakers during human creative discussion, but executable prompts should translate that
discussion into concrete composition, lighting, colour, texture, camera and performance direction
instead of relying on a name as a style shortcut.

### Purpose and run shape

Each Stage 2 run is a controlled production-quality test, with one main variable such as a new
location, physical action, cast pairing, dialogue mood or bounded product feature. Keep one
location, a small cast, bounded spend and sequential paid requests. Prefer a shorter scene with
fully admitted shots over a longer scene assembled from compromised coverage.

Stage 2 may grow the feature set gradually. Add at most one bounded feature or capability per run
or mini-cycle, state the hypothesis and regression risk, and require every existing hard gate to
continue passing. Promote a feature into the baseline only after it works in two accepted runs;
otherwise keep it experimental or remove it without disturbing the proven path.

Every run must declare before generation:

- its `series_id`, `season_id`, `episode_id` and `sequence_id`, plus the sequence's scene records,
  even when the current test generates only one sequence containing one scene;
- the story beat, essential visible actions and required start/middle/end action states;
- typed setup and planned-shot lists with camera side and height, lens intent, shot size, subject
  scale, headroom, look room, eyeline, movement and edit purpose;
- a location reference brief with ranked visual anchors and prohibited substitutions;
- persona cards for principals and a casting plan for the visible ensemble;
- a voice/accent brief tied to each persona;
- a location-specific ambience and foley cue sheet;
- hard admission criteria that cannot be downgraded to a known limitation after generation.

### Non-negotiable picture contract

- The delivery and every accepted intermediate must be native landscape 16:9 with square pixels:
  1920×1080 or 1280×720. Text-to-video sources must also be native 16:9. The sole source exception
  is the proven station-scene lip-sync path: a 1:1 raw avatar performance derived from an approved
  native-16:9 scene reference, converted through a preplanned exact-16:9 crop with no padding. Its
  crop must retain at least 75% of source width and 45% of source height and pass every-frame
  face/mouth review. A landscape wrapper is not sufficient.
- Reject portrait-origin clips, rotation, pillarboxing, blurred/mirrored side extensions and crops
  whose purpose is to disguise a vertical source. Detect and record source and display aspect ratio
  before any edit or cost-bearing downstream step.
- The square-avatar exception never permits portrait input or output, side fill, a cut hairline,
  hidden mouth, or an improvised crop. The square reference must be traceable to one approved paired
  16:9 scene so it cannot silently create a second environment or persona realization.
- Use an intentional television/film coverage pattern: geography-establishing master, readable
  medium or two-shot coverage, motivated close coverage, inserts and reactions. Do not build a
  scene mainly from repeated talking-head profile close-ups.
- Match the declared shot size. Keep intentional headroom and look room; place eyes deliberately;
  keep the forehead, eyes, nose, mouth and chin safely in frame for ordinary close-ups. A forehead,
  chin, mouth or face may cross an edge only for a storyboarded extreme close-up approved before
  generation, never as a crop repair.
- During every spoken interval, keep the complete lips, chin and jaw movement visible with a safe
  margin. A shot whose crop or foreground obstruction hides the mouth cannot prove lip sync and is
  rejected as dialogue coverage.
- Preserve enough shoulder and environmental context to make the counter axis and performance
  readable. A foreground shoulder may support an over-the-shoulder composition but may not swallow
  the frame or obscure the speaking face.
- Review each shot at normal speed from first through last frame and sample at least two frames per
  second plus the first frame, last frame and cut handles. Contact sheets must label shot ID and
  timecode and preserve each sampled frame's 16:9 shape.
- Cropping is a creative reframe only when the native landscape source has safe overscan and the
  crop passes every-frame review. Cropping is not an identity, orientation or missing-anatomy fix.

### Edit rhythm, intro/outro and stitch integrity

- Give the environment an opening beat before the first line or essential action: normally 2–4
  seconds, long enough to read the place, geography and ambience without feeling like dead air.
- Leave at least 3 seconds after the final spoken line or essential action, normally 3–5 seconds,
  so the reaction and environment can resolve. Use living micro-motion rather than an unexplained
  freeze frame.
- Unless a storyboarded cold open or hard ending is explicitly approved, fade picture and ambience
  in together over about 0.5 seconds and fade them out together over about 0.5 seconds. Preserve the
  dialogue/music relationship and avoid cutting speech with a fade.
- Editorial cuts may be noticeable and motivated; technical stitches inside one apparent take may
  not be. A stitch must not introduce a pose, face, gaze, scale, crop, background, lighting, colour,
  frame-cadence, room-tone or lip-sync jump.
- Review every internal stitch frame by frame across at least 0.25 seconds on both sides and then at
  normal speed with sound. Check audio for clicks, phase changes, bed dropouts and abrupt noise-floor
  shifts. Record both source boundaries and final-timeline timecodes.
- If a repair cannot make an internal stitch invisible, replace it with a motivated cut to a
  compatible angle, insert or reaction, or reject/regenerate the shot. Do not hide the seam with a
  blur, freeze or arbitrary transition.

### Essential action legibility

An action required to understand the story must be visible without explanation from the manifest,
prompt or auditor. Show a readable initiation, contact/transfer and completion with consistent prop
ownership and screen direction. Review the action in the assembled scene at normal speed, not only
as isolated stills.

For a future BC Care Card beat, the patient must visibly own and present one card, the nurse must
visibly receive it across the established counter plane, and the card must finish on the staff side
before the check. The face stays unreadable, but privacy may not make the transfer narratively
invisible. If the handoff is skipped, ambiguous or begins after transfer, reject the sequence.

### Dialogue and lip-sync acceptance

- Treat generation sync and edit sync as separate questions. Identical picture/audio trims and rate
  changes preserve source timing but do not prove that the generated mouth ever matched the voice.
- Resolve the dialogue speaker through the series manifest before audio generation. The request must
  carry character ID, persona version, voice-realization ID and approved audition hash. A CLI voice
  alias or prompt-local voice string is not a persona and may not override the inherited binding.
- Compare the rendered voice to the approved audition by human listening. ASR, waveform hashes,
  PCM PSNR and provider metadata cannot establish perceived gender, age, timbre, accent or casting.
- Review every spoken interval at normal speed with sound. Then inspect representative plosives and
  closed-mouth consonants frame by frame, including the start and end of each utterance. Reject a
  persistent audible lead/lag, mouth movement during silence or speech with a still/closed mouth.
- Where an objective audiovisual sync tool is available, target absolute offset within 80 ms and
  retain its confidence/output, but human perceptual approval remains mandatory. Absence of an
  objective score must never be replaced by a claim based only on shared edit transforms.
- Never repair sync by independently shifting, trimming or retiming picture and voice unless the
  new offset is documented and the complete result is re-audited. If the source is visibly off,
  regenerate or replace the dialogue shot.

### Surrey environment fidelity

Treat `docs/ideas_for_scenario_testing/Screenshot for scenario 2 - clinic reception.png` as the
target environment brief for this scenario, not loose colour inspiration. Preserve facility
privacy by omitting logos, names and readable signage, while matching the design language as
closely as the approved model and budget allow.

Required high-weight anchors for this clinic test are:

- bright, contemporary South Surrey urgent/primary-care character rather than a dim generic
  hospital waiting hall;
- saturated turquoise/teal clinical bays, wall planes or partitions as dominant architecture;
- pale ceiling and flooring, clean daylight and an airy neutral exposure;
- light-wood, modular reception or triage stations rather than one long dark-wood counter;
- clean open circulation and small waiting clusters rather than rows of auditorium-style chairs.

Before paid generation, make a reference-to-plan comparison that lists what will be reproduced,
abstracted and excluded. Use reference-conditioned generation when an approved model supports it;
otherwise compile the high-weight anchors explicitly into every environment prompt. Before final
promotion, compare the master and representative coverage frames side by side with the reference.
At least four of the five high-weight anchors must be clearly present, and a human reviewer must
accept the overall environmental resemblance. Technical continuity within the wrong room fails.

### Surrey-representative casting and voices

- Cast the principals and visible ensemble to feel credibly drawn from ethnically and culturally
  diverse Surrey, BC. Across Stage 2 runs, do not repeatedly default to a white-presenting pair with
  diversity confined to anonymous background figures.
- Give every recurring principal a series-owned, versioned canonical persona and reference pack:
  age baseline, role, self-described cultural or community background when story-relevant, local
  history, language history, durable appearance, manner, relationships and voice. Do not infer
  culture, language or accent from appearance.
- Inherit the canonical persona into season and episode character state. Sequence and scene records
  may direct current wardrobe, knowledge, objective, emotion and performance, but may not silently
  change identity, background, base appearance, accent or voice. Record deliberate development as
  an explicit, effective-dated persona version or continuity event.
- Tie accent and speech rhythm to the written persona. Use natural Lower Mainland/Canadian English
  when appropriate; use another accent only when the persona supports it and the available voice
  can render it consistently and respectfully. No caricature, accent switching or generic
  “ethnic” direction.
- Audition and human-approve the voice with a short dry sample before paid lip-sync. Record the
  selected voice, language/accent direction and reviewer decision in the run manifest. If the model
  cannot produce the intended accent convincingly, revise the casting/voice plan before generation.
- Give the approved casting realization a stable `voice_realization_id`. Retain the audition audio,
  SHA-256, provider/model/voice version, synthesis settings and human perceptual decision. Bind every
  line and sequence-wide performance master to that ID. Reject missing, conflicting or ad-hoc voice
  assignments before any paid motion request.
- Evaluate representation across the run set, not with a rigid quota inside one scene. Casting must
  remain story-plausible and principals must be fully realized characters rather than tokens.

### Ambient sound and foley

- Build a location-specific, clearly licensed ambience bed—for a clinic, restrained HVAC, distant
  reception activity, soft footsteps and indistinct waiting-room movement. A generic room-tone
  file by itself is not acceptance.
- Ambience must be faint but perceptible throughout, especially for at least the opening beat,
  dialogue pauses and the final reaction/outro. Keep it continuous across picture cuts, with no
  obvious loop, abrupt level jump or synthetic repetition.
- Apply the planned approximately 0.5-second ambience fade-in and fade-out with the outer picture
  fades. The bed must remain perceptible after the opening fade and through the longer ending beat.
- As a starting mix target, keep ambience roughly 15–22 dB below dialogue and approximately
  -38 to -30 LUFS short-term in ambience-only passages, adjusted by ear for the material. An
  intended ambience passage with mean level below -50 dBFS fails unless the shot plan explicitly
  calls for artistic silence.
- Add story-required foley at the visible contact point—a card slide/hand-off, restrained cough or
  footsteps—without masking speech. Picture and cue timing must be reviewed together.
- Pass both a measured loudness report and a human audibility review on headphones and ordinary
  speakers. The existence of an audio stream or non-zero samples is not proof that the environment
  can be heard.

### Stage 2 audit and admission gates

| Gate                            | Pass condition                                                                                                                                                                                                                                                    | Required evidence                                                                 |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| Native format                   | Every accepted source/intermediate/final is square-pixel 16:9 landscape; zero portrait-derived or side-filled intervals                                                                                                                                           | ffprobe inventory tied to the timeline manifest                                   |
| Cinematic composition           | Declared shot size, safe face framing, headroom/look room, subject placement and visual variety pass throughout                                                                                                                                                   | labelled per-shot sheets plus normal-speed human review                           |
| Functional environment logic    | Furniture and equipment are operable, not decorative: monitors face operators, keyboards align with them, devices are supported and reachable, and action paths do not collide                                                                                     | first/middle/last frames plus prop-and-workstation spatial audit                   |
| Anatomy and contact integrity   | Hands and limbs retain plausible left/right structure, finger count, attachment and articulation; contact points do not fuse, reverse, morph or pass through props                                                                                                  | dense action frames plus normal-speed review before source admission               |
| Response-anticipation eyeline    | A speaker asking a question or inviting an answer maintains polite partner eye contact through a usable post-line handle; a downward or disengaged end glance blocks the take                                                                                       | line-end frames plus normal-speed performance review                              |
| Motion stability                 | Locked and restrained shots have no camera jitter, object buzz, edge shimmer or erratic hand/prop motion; close action inserts receive frame-by-frame stability review                                                                                              | normal-speed playback plus dense contact sheet around the action                   |
| Essential action                | Every required action reads as initiation → contact/transfer → completion with correct ownership                                                                                                                                                                  | action-state sheet and assembled-scene review                                     |
| Dialogue visibility and sync    | Complete mouth/jaw remains visible; every line has human-approved perceptual sync and no persistent lead/lag                                                                                                                                                      | utterance-level sync review and objective offset when available                   |
| Reference fidelity              | At least four of five high-weight location anchors and overall resemblance pass                                                                                                                                                                                   | side-by-side reference/master/coverage board with human decision                  |
| Persona, casting and voice      | Series-owned persona/version inheritance, Surrey-representative casting and persona-consistent, non-caricatured voices pass                                                                                                                                       | series persona/reference-pack manifest, episode state and voice audition decision |
| Ambient sound                   | Location ambience is continuous, faint but perceptible in intro, pauses and outro; required foley is synchronized                                                                                                                                                 | cue sheet, loudness measurements and two-device listening decision                |
| Edit rhythm and seams           | Opening reads, ending holds at least 3 seconds, outer picture/sound fades are about 0.5 seconds, and no internal technical stitch is perceptible                                                                                                                  | cut/stitch manifest, boundary inspection and normal-speed human review            |
| Continuity and safety           | Geography, identity, wardrobe, gaze, privacy, anatomy/contact, text and audio sync retain their existing hard gates                                                                                                                                               | shot and final-sequence audits                                                    |
| Vocabulary and evidence quality | Series, season, episode, sequence, scene, persona version, setup, take, clip, source interval, shot, cut and transition IDs are used consistently; no hard failure is promoted as `pass_with_known_limitation`; all repairs have exact source and time boundaries | immutable admission records and final timeline provenance                         |

Audit in this order: manifest and native-format preflight; reference/persona/voice preflight; source
shot admission; action and crop review; rough-cut cinematic and continuity review; sound mix review;
then final technical and human acceptance. A model or checklist is never the sole aesthetic
authority, and a high score on privacy or continuity cannot compensate for a different room,
portrait footage, cut faces, illegible story action or inaudible sound.

### Stage 2 exit gate

Complete Stage 2 only after two contrasting test scenes pass every hard gate with:

- zero portrait-derived accepted seconds and zero accidental face-edge cuts;
- native cinematic 16:9 composition throughout and human-approved shot variety;
- every essential prop action legible at normal speed;
- complete mouth visibility and human-approved lip sync for every spoken interval;
- human-approved reference-environment fidelity where a target reference is supplied;
- series-owned persona/version inheritance, Surrey-representative casting and approved matching
  voices/accents;
- audible location ambience in the opening, pauses and ending, with matched approximately
  0.5-second outer fades and a final hold of at least 3 seconds;
- no perceptible internal stitch, audio-bed dropout or arbitrary repair transition;
- retained series/season/episode/sequence/scene persona and production lineage through
  setup/take/clip/shot/cut, plus source interval, prompt, seed, edit-boundary, model, cost, hash and
  admission evidence.

Add capabilities gradually under the one-feature rule. Defer large jumps—long-form or
multi-location production, simultaneous provider expansion and automated aesthetic authority—until
the complete Stage 2 gate is met twice.

## Retry policy

For a rejected or failed shot:

1. Reconcile whether the original request was billed.
2. Retry one confirmed transient failure with the same request only if budget is available.
3. Try one new seed.
4. Apply one conservative prompt repair.
5. Stop for human redesign.

No provider self-retry, recursive retry, automatic upgrade to a partner model, or parallel retry is permitted.

## Evaluation order

1. Native technical validity: decoding, duration, source/intermediate/final orientation, square-pixel
   16:9 resolution, blank frames, freezes, cadence and audio integrity.
2. Structured checks: intended framing, face/mouth safety, number of people, location anchors,
   wardrobe, screen direction, essential action states, prop ownership and privacy.
3. Dialogue and sound checks: mouth visibility, perceptual/objective lip sync, ambience audibility,
   foley timing, stitch continuity, outer fades and final loudness.
4. Qwen-VL review of labelled sampled frames/contact sheets and side-by-side reference boards.
5. Human normal-speed review of composition, reference fidelity, casting/voice authenticity, acting,
   action legibility, continuity, emotional effect, dialogue rhythm, seams and final edit quality.

A model is never the sole acceptance authority.

## Definition of success

The proof succeeds if it produces:

- one coherent 12–30 second scene in one location;
- a measurable continuity result rather than an unsupported claim;
- a complete prompt, seed, model, cost, and hash trail;
- a reproducible cost per accepted second;
- clear evidence about whether DeepInfra-hosted OSS text-to-video is sufficient for the next stage.

## Accepted clinic Stage 2 baseline

The 2026-08-03 clinic master is the first accepted Stage 2 sequence. Its normative package is
`runs/clinic-stage2-20260803T060048Z/final/clinic-stage2-sequence-v3.mp4`, the adjacent manifest and
timeline, the final v3 contact sheet and `audits/final-stage2-audit-v3.json`.

Subsequent runs must:

- name separate facial-lighting, composition/depth and palette references, including properties
  that must not be copied;
- use flatter pastel narrative colour and readable skin exposure; reject contrast/plasticity at the
  boundary-sheet gate;
- audit functional props and anatomy at dense frames, with crowd/background state continuity;
- keep visible dialogue audio-conditioned and source-locked, then verify mouth sync, persona,
  wardrobe, pose/posture, gaze, screen direction, palette and performance across the whole sequence;
- use independent clinic/location speech for chatter, never principal lines or procedural noise,
  and measure ambience after final loudness normalization;
- preserve response-anticipation eye contact, answer every unresolved spoken beat, and retain a
  living outro of at least three seconds;
- use straight cuts unless a separately audited stitch is truly imperceptible, with approximately
  0.5-second outer fades;
- keep story content in manifests and runtime invariants generic.

For multi-turn persona dialogue, generate or record one sequence-wide performance master per
speaker whenever the provider supports it. Direct the complete emotional and prosodic arc once,
spell pronunciation-sensitive abbreviations in spoken form, split only at intentional pauses, and
derive every visible synchronized turn from those lossless segments. Independently generated lines
from nominally similar voices fail persona continuity when timbre, diction, pace or dramatic weight
drifts. Persist the performance master and split map as provenance.

Background ensemble is continuity state. Name the established extras and positions in the master,
carry them through every shot that reveals the same depth, and permit their absence only when a
declared reverse or tighter setup physically excludes that part of the room. A person appearing or
vanishing within a visible established region blocks promotion.

## Current Maya/Kenji production outcome

`runs/clinic-cosmos-final-v03` is the strongest repaired clinic candidate: 35.459 seconds, 720p
master plus 480p review copy. It removes the static opening, replaces the noise-like ambience with
multi-voice clinic activity, cuts speaking pictures at audible performance boundaries, corrects
`BC Services Card`, and uses an official-layout fictional `SAMPLE` prop. Its automated audit passes;
final human audiovisual promotion remains pending. The execution policy learned by v02 and v03 is:

1. Bind selected provider realizations to provider-neutral voice personas before dialogue synthesis.
2. Generate one timestamped performance master and independently ASR-audit it.
3. Derive turn boundaries from exact script-to-ASR word alignment, never provider segment timestamps
   alone; pad without stretching or resampling.
4. Use Wan for retained single-speaker picture performance and Cosmos only for face-free spatial
   action that passes dense contact review.
5. Use asynchronous webhooks for long DeepInfra jobs; keep the queue timeout short and callback wait
   separately bounded. Hash decoded outputs, retain compact receipts, and prune duplicate data URLs.
6. Assemble typed native-16:9 lineage locally, use semantic spatial ambience beneath dialogue, and
   use a motivated audio lead when it hides a known picture/audio boundary without hiding action.
7. Treat automated visual, waveform and ASR evidence as a review gate. Human normal-speed playback
   remains required before promotion from review candidate to accepted final.
8. Plan living wide/master coverage before singles; a static visual anchor is not finished footage.
9. Give essential actions target onset/contact/release/completion timecodes and separate exact prop
   pixels from generated motion through local tracking and compositing.

The cumulative conservative monetary accounting through v03 is US$7.82976088, with ElevenLabs
credits reported separately. No further clinic request is authorized; the user chose stage-level
learning over another repair.

## Program Stage 3 — Cinematic grammar and versatile series production

Status: planned; generation not authorized.

Stage 3 develops cinematic craft in all its dimensions: dramaturgy, character/relationship/plot
arcs, theme, narrative point of view and time, screenplay/dialogue/narration, directing and acting,
mise-en-scene, cinematography and lighting, storyboarding and previs, editing, sound/music/silence,
VFX/compositing, colour/finishing, continuity, production management, rights and ethics.

Its priority order is independent A/B/C episode architecture; story intention; locked animatic and
living coverage grammar; directing and performance; editing and sound; mise-en-scene and
cinematography; then temporal action and exact props. Local model benchmarking serves those crafts
rather than becoming the goal.

The complete plan and machine-readable contract are:

- [STAGE-3-CINEMATIC-SERIES-PLAN.md](STAGE-3-CINEMATIC-SERIES-PLAN.md)
- `productions/stage3-cinematic-versatility.json`

Stage 3 requires one accepted 5–12+ minute episode built sequence by sequence across multiple sets,
with A/B/C plots that have independent objectives and causally or thematically meaningful
intersections. A 60–90 second multi-set vertical slice is the spend-control gate before full
production. The stage also requires a complete no-generation preproduction packet for a contrasting
second project, proving that the engine is portable rather than clinic-specific.
