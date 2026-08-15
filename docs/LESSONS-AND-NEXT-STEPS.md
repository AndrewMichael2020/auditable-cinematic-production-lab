# Stage retrospective: lessons and next steps

## Current status — Stage 3 planned

Stage 2 is strategically closed with declared carry-forward debt. Its strict two-sequence exit gate
was not met. `clinic-cosmos-final-v03` is the strongest repaired review candidate, but it still has a
transient card blip, slow handoff motion, no living wide coverage and pending human audiovisual
acceptance. The user chose to generalize those lessons in Stage 3 instead of repairing the clinic
scene again. No Stage 3 generation or local-model installation is authorized yet.

The earlier `clinic-full-sequence-20260803T184456Z` remains rejected after human playback found
visible lip asynchrony and a female-sounding patient voice. Its decisive lesson still holds: a visual
persona is not a production persona. Voice aliases in a request are implementation parameters, not
canonical casting, and audio transport does not prove mouth synchronization. The historical audit
is in [CLINIC-FULL-SEQUENCE-POSTMORTEM.md](CLINIC-FULL-SEQUENCE-POSTMORTEM.md); the current decision
is in [STAGE-2-CLOSEOUT.md](STAGE-2-CLOSEOUT.md).

## Result

This stage is a success. The pipeline produced a coherent 15-second scene with a wide master,
movement, four dialogue turns, visible lip sync, changing emotion, and a cliffhanger. The live
avatar attempts cost US$0.55 actual against US$1.00 reserved. The final media, paid sources,
decisions, hashes, and cost ledger are preserved in `runs/cliffhanger-20260802T235825Z/`.

The next goal is repeatability across scenes, not more infrastructure.

## What we learned

- **Geography comes before coverage.** A 2–4 second wide master makes later close-ups readable and
  gives movement, screen direction, distance, and the environment a shared truth.
- **Gaze is blocking, not decoration.** Every actor needs a named target and screen direction. “Do
  not look at camera” helps, but the draft still needs visual inspection: Mara's first calibration
  take drifted toward the lens and was correctly rejected.
- **Count people, then identify them.** The raw Eli take invented a second man; it was not Mara.
  Cropping is valid only when an every-frame review proves that the unwanted person never enters
  the delivered frame. Otherwise regenerate.
- **Audit the physical world early.** Platform and track relationships, object support, safe actor
  placement, garment construction, hands, scale, and eyelines should be settled before paid
  generation. Attractive but impossible imagery is still a failed shot.
- **Keep text out unless the story truly needs it.** Light, weather, colour, architecture, spacing,
  and sparse icons communicate more reliably than generated signs or explanatory words.
- **Treat synchronized picture and sound as one asset.** Trim only expendable outer silence and
  change picture and audio speed together. Internal dialogue cuts or independent retiming risk
  breaking otherwise strong lip sync.
- **Short, playable dialogue wins.** One intention and one emotional change per turn give the model
  a clearer performance target than dense prose.
- **Reuse proven assets intentionally.** Reusing the accepted wide master and compact actor
  references improved continuity, avoided another risky generation, and kept cost low.
- **Preserve evidence, not clutter.** Keep paid raw media, accepted edits, references, ledgers,
  manifests, final QA, hashes, and one final contact sheet. Previews and intermediate frame sheets
  are deterministic and can be pruned after their decisions and hashes are recorded.

## Checklist for the next paid run

1. Plan one 12–15 second scene with a 2–4 second wide master and three or four short dialogue turns.
2. Fix the camera axis, safe zones, object layout, actor count, and wardrobe before generation.
3. Give every visible actor a story target and left/right eyeline; direct lens gaze is a blocking
   failure unless the script explicitly calls for it.
4. Forbid incidental text and avoid unnecessary public-space icons.
5. Make paid requests sequentially, reserve worst-case cost first, and stop on unknown billing.
6. Review every frame of any crop used to repair identity, person-count, or edge-intrusion defects.
7. Assemble without separating synchronized audio from its picture; then check decode, duration,
   black frames, loudness, dialogue rhythm, and the final emotional beat.
8. Retain the traceable core and prune only artifacts that can be reproduced from retained media.

## Pareto next steps

1. **Run one contrasting robustness scene.** Use a different environment—such as the existing
   [clinic reception reference](<ideas_for_scenario_testing/Screenshot for scenario 2 - clinic reception.png>)—while keeping two actors, one location, one master, and four turns. This tests whether
   the result came from the pipeline rather than one unusually favorable platform setup.
2. **Add one controlled physical action.** A door opening, object pickup, or seated-to-standing move
   is enough to test hands, contact, scale, and continuity without turning the scene into an action
   sequence.
3. **Add a subtle continuous ambience bed.** Room tone or location ambience beneath the silent
   master and dialogue will make the edit feel unified. Use a local or clearly licensed asset;
   another speech provider is unnecessary while the current voices work.
4. **Keep a simple shot-admission record.** Before assembly, record pass/reject for geography,
   person count, identity, gaze, wardrobe, text, anatomy/contact, and audio sync. This can remain a
   small JSON report rather than a new service or UI.
5. **Repeat twice before scaling.** If two contrasting scenes pass at similar quality and cost,
   then consider objective lip-sync scoring, reusable ambience libraries, and longer sequences.

For the next complete test, target US$1–1.50 actual and retain the existing US$3 hard stop. A new
wide master is worth paying for only when the setting or blocking genuinely changes.

## Deliberately defer

- multi-location episodes and long-form continuity;
- automatic paid retries or provider fallback;
- dashboards, orchestration services, and asset-management UI;
- broad TTS/provider expansion; first prove mouth-visible, persona-matched, perceptually synchronized
  speech with one deliberately selected path;
- broad model comparisons without a specific failure the new model is meant to solve.

The stage gate is now **repeatable quality under a small budget with gradual, evidence-backed
feature growth**. Add one bounded feature at a time, keep the existing quality gates green, and
promote it into the baseline only after it succeeds in two accepted runs.

## Clinic robustness result

The contrasting clinic test completed a 49.69-second, twelve-interval scene for US$2.625 actual
against US$3.075 reserved. The final, paid sources, rejected takes, dialogue edits, append-only
ledger, hashes, staged audits and timeline provenance are in `runs/clinic-20260803T011736Z/`.

A later cinematic re-audit found that this is a pipeline and evidence success, but not an accepted
Stage 2 scene. The earlier `pass` decisions remain evidence for geography, privacy, identity,
screen direction and provenance only. They did not evaluate several requirements that are now hard
gates, and the earlier lip-sync pass is withdrawn.

Lessons that generalize:

- Generate the room first. A dedicated environment-master prompt improved crowd, counter and
  circulation geometry because it stopped asking one request to solve close face detail too.
- Treat privacy props as states, not descriptions: face-down, edge-on, moving, occluded or defocused.
  Admit only the safe interval when a longer take starts inventing card-like objects.
- Audit transitions after local repair. Crops, background blurs and reaction-tail selection can fix
  one defect while introducing lens gaze, missing mouths or an inconsistent frame shape.
- Reserve avatar cost from provider output risk, not only requested dialogue length. A nominal
  eight-second turn returned 12.2 seconds; its exact known cost was reconciled without retrying.
- Live partner-avatar references need public HTTPS transport. Reject inline/local images before
  reservation instead of paying for a request the provider cannot fetch.
- Longer scenes remain cheapest when only the master and physical-action insert use video models;
  compact stable character references can carry the dialogue coverage.

### Clinic cinematic re-audit — 2026-08-03

What held up:

- The opening wide establishes the counter, waiting area, public/staff sides and general geography.
- Principal identity, wardrobe, light direction and conversational screen direction are reasonably
  coherent. Picture and audio received matching edit transforms, although that does not establish
  generated lip sync.
- Card and screen details remain unreadable, with strong cost, source, hash and timeline provenance.
- Paid failures were bounded and reconciled rather than hidden or retried recursively.

What failed the new Stage 2 bar:

| Finding | Evidence | Decision |
|---|---|---|
| Portrait footage inside a landscape wrapper | All nine accepted raw avatar outputs are 768×1152. Dialogue coverage plus the derived reaction accounts for 38.873 of 49.686 seconds, or 78.2% of the delivery master. Most clips were tightly cropped; `c06` used blurred same-frame side extensions. | Block |
| Accidental face cuts and weak composition | `final-c07-nurse-card-request-contact-sheet.png` reduces the nurse to partial face/eyes in several samples. The final sheet also shows abrupt scale jumps, partial faces in `c03` and `c11`, dominant foreground obstructions, repeated profile close-ups and too little environmental/shoulder context. | Block |
| Lip sync is hidden or visibly off | Several dialogue crops remove or obscure the mouth, so synchronization cannot be assessed. Where the mouth is visible, the final has perceptible voice/mouth offset. The previous audit treated identical audio/video trim and rate transforms as proof; those transforms only preserve the source timing, including any generated offset. | Block |
| Environment does not closely match the supplied reference | The reference is bright and airy, with dominant turquoise clinical bays, pale ceiling/floor, light modular desks and open small seating groups. The result is a dimmer beige hospital hall with one long warm-wood counter and rows of teal chairs. The recorded use policy explicitly treated the image as loose inspiration, did not send it as a generation reference and excluded source-composition reproduction. | Block |
| Surrey casting and accent intent is incomplete | Separate nurse and patient descriptions and visual references were controlled within the run, which helped identity continuity. However, they are not series-owned/versioned personas, omit cultural/community, language-history and accent fields, and the retained request records do not establish persona-matched voice selection or audition. Background diversity cannot substitute for protagonist diversity. | Block |
| The BC Care Card handoff is not legible | `c07` verbally asks for the card, but the following insert does not clearly show the patient owning, presenting and transferring it to the nurse before the check. Existing prop audits infer continuity from states; the action itself is not readable at normal speed. | Block |
| Ambience exists but is effectively inaudible where it matters | A room-tone file is present, yet the final opening measures about -82.5 dBFS mean/-69.5 dBFS max and the outro about -74.0 dBFS mean/-55.7 dBFS max. This is technical non-silence, not a perceptible clinic environment. | Block |
| Outro and finishing rhythm are under-resolved | The last interval is a 2.851-second still-frame hold derived from earlier footage, with effectively inaudible ambience and no planned matched picture/sound fade. It does not provide a living, cinematic resolution. | Block |
| The audit schema over-promoted the cut | `blocking_and_framing` checked axis and orientation, not cinematic composition or face safety. No hard rules covered native source orientation, reference similarity, persona/voice authenticity, essential action legibility or ambience audibility. The final audit therefore reported `pass` for conditions it never tested. | Block |

Lessons to carry forward:

- **Retire models that miss the cinematic quality bar.** Early tests of
  `FastVideo/FastWan-QAD-FP8-1.3B` produced simplified glossy/cartoon-like people rather than a
  lower-cost preview of the intended cinema. It was evaluated, did not meet the expected quality,
  and is no longer registered or executable. Its retained run records exist only as provenance.
- **Reuse the station lip-sync contract exactly.** The accepted station scene used 512×512
  single-person references, 960×960 synchronized avatar outputs and preplanned 16:9 crops with
  identical picture/audio trim and rate transforms. Native landscape inputs returned HTTP 500,
  while the square path reproduced the good synchronization. Stage 2 therefore permits this one
  evidence-backed square-performance exception—never portrait footage, side fill or a crop that cuts a
  face—and requires the square reference to derive from an approved paired 16:9 scene.

- **Validate source orientation, not the final wrapper.** Scaling, cropping or side-filling a
  portrait source into 1280×720 does not make it cinematic landscape footage.
- **Do not use crop repair to manufacture a shot.** A crop is admissible only from a landscape
  source with safe overscan, intentional composition and an every-frame face/anatomy pass.
- **Separate continuity compliance from cinematic acceptance.** Correct axis, identity and privacy
  are necessary, but a badly composed close-up still fails.
- **Prove lip sync from the mouth and sound, not the edit recipe.** Keep the complete lips and jaw in
  frame, review every utterance perceptually and inspect consonant closures. Shared trims cannot
  convert an off-sync source into an accepted shot.
- **Turn visual references into weighted anchors.** Record which architectural features define the
  target, compare them side by side and require human resemblance approval. Loose colour borrowing
  is insufficient when the brief asks for a close environmental match.
- **Story actions must read on screen.** Prop state and ownership records cannot replace visible
  initiation, transfer/contact and completion. Privacy-safe does not mean narratively invisible.
- **Promote controlled run personas into series canon.** Keep the useful separate character
  references, but own and version canonical persona, cultural/local context, language history,
  accent direction, casting realization, audition and approval at series level. Episodes inherit
  that canon and add explicit state; they do not redefine it. Never infer an accent from appearance
  or direct a caricature.
- **Mix for perception, not track existence.** Measure the ambience-only opening and ending, then
  listen on headphones and ordinary speakers. Preserve a faint clinic bed through pauses and add
  synchronized foley for required visible actions.
- **Finish the outer edges and hide only technical seams.** Establish the environment before the
  first line, hold a living final beat for at least three seconds, and default to matched picture
  and ambience fades of about 0.5 seconds. Inspect every repair stitch frame by frame and at normal
  speed; when it remains perceptible, use a motivated editorial cut or reject the shot.
- **A hard visual or sound failure cannot become a known limitation.** Repair within the bounded
  policy or reject the shot/run; successful billing and provenance do not promote it.

Pareto next steps:

1. Reject portrait output at source admission and prove one complete scene with native 16:9
   dialogue coverage before optimizing anything else.
2. Re-run the clinic only from a reference-anchor brief that prioritizes the supplied turquoise,
   bright, modular South Surrey reception environment.
3. Recast with written Surrey-representative personas and audition persona-matched voices before
   lip-sync generation.
4. Storyboard and shoot the BC Care Card handoff as a complete privacy-safe action, including
   patient ownership, transfer and nurse receipt.
5. Add a location-specific ambience/foley cue track and verify that it is faint but audible in the
   intro, gaps and longer outro on two playback devices; apply matched approximately 0.5-second
   outer picture/sound fades.
6. Emit exact internal edit boundaries, reject perceptible stitch seams and run the new Stage 2
   gates—including utterance-level mouth-visibility and lip-sync review—before any final promotion.
# Functional layout is a blocking visual property

A wider desk is not sufficient if the objects on it do not form a usable workstation. The review of
`edf-corrected-workstation-card-reference-v2.png` exposed an awkward monitor placement that an earlier
pass incorrectly accepted. Stage 2 screenshot and contact-sheet audits must now treat practical
operability as spatial continuity: monitor screen orientation and supported base, monitor–keyboard
alignment, operator reach, reader placement, and an unobstructed handoff path all require explicit
evidence. A frame that merely contains the requested objects remains blocked.

# A synchronized question still fails if the actor abandons the listener

`d7b36f56-d634-4700-a973-e2ccbdad3cd8.mp4` preserved the new nurse-side composition and visible
speech, but Amrit lowered her gaze after asking what brought Daniel in. A question beat must include
the anticipation of an answer: polite partner eyeline continues through the post-line handle. Stage 2
now blocks question takes that end on a keyboard glance, downward gaze, camera gaze, or other visible
disengagement, even when their lip sync is otherwise acceptable.

# Dialogue model choice depends on the required shot, not lip sync alone

`PrunaAI/p-video-avatar` retained good synchronized speech for a single-person train-station setup,
but the clinic tests showed two different failure modes: a single-person reference caused invented
listeners when strong response-eyeline language was added, while a paired landscape reference was
reframed as an over-close split screen with a black divider. `Wan-AI/Wan2.6-I2V` with its documented
synchronized audio input preserved the native paired clinic composition in the bounded greeting
test. The run may therefore expand that path only to nine sequential candidates under the existing
monetary cap. Each request is explicitly limited to 5, 6 or 7 seconds and reserved at the verified
per-second rate so complete persona audio is never clipped or time-compressed merely to fit a five-
second default. Perceptual and human lip-sync review remain mandatory.

## Clinic Stage 2 completion retrospective — 2026-08-03

The corrected 38.51-second clinic sequence passes the Stage 2 gate at US$11.800723 actual. It is the
first accepted Stage 2 run, not yet the two-run exit condition.

- **Give each reference one job.** `8dc…` governs facial texture, eye light and intimate acting;
  `edf…` governs composition, spatial depth and restrained colour but not its underexposed faces;
  `shot03-patient-symptom-contact-sheet.png` governs the whole-cut clinic palette.
- **Cinematic is not high contrast.** Boundary QA rejected a contrast-heavy plastic finish. The
  accepted master lifts shadows, compresses contrast and saturation, uses pastel teal/neutrals and
  fine grain, and keeps both faces readable.
- **A negative prompt cannot rescue a glossy plate.** Begin with textured, non-advertising source
  imagery, then direct practical light, visible adult skin, asymmetric micro-expression and framing.
- **Workstation logic is a depth contract.** Audit monitor support and operator axis, keyboard
  separation, reader reach and an unobstructed card path—not merely whether all objects exist.
- **Anatomy means the whole kinetic chain.** Inspect shoulder→elbow→wrist connection, palm
  orientation, handedness, ownership, contact and release at dense time samples.
- **Background people are continuity state.** They may be off screen in a tighter setup, but must
  persist whenever the established waiting-room depth returns.
- **A question needs eye contact and a narrative answer.** Amrit holds the listener after asking;
  Daniel's “How much?” is followed by her truthful uncertainty before the living outro.
- **Off-screen dialogue is honest when the mouth is unverified.** It must never hide a required
  action. The card remains visible; only Daniel's short question moves off screen.
- **Lip sync is sequence-wide.** Every visible line uses audio-conditioned picture; picture and
  audio remain source-locked through identical trims. Palette, identity, wardrobe, pose/posture,
  screen direction, gaze and acting restraint are also checked across every cut, not shot by shot.
- **Voice continuity begins before lip sync.** Four separately rendered nurse lines produced a
  conspicuous closing-voice mismatch even though the final line itself was clear. The accepted v3
  records one 19.2-second dramatic Amrit performance, uses spoken BC/MSP diction, splits only at
  deliberate pauses and conditions all four visible turns from that master. A shared voice label is
  not proof of shared timbre, prosody or emotional arc.
- **Extras are spatial state, not decoration.** The same two waiting patients persist whenever the
  opening waiting-area depth returns. Singles may omit them only when the declared reverse angle
  places their positions outside frame; an empty established position is a blocking discontinuity.
- **Noise is not chatter, and principal dialogue is not ambience.** Use separately generated,
  location-specific conversations, diffuse them, keep them secondary and measure after mastering.
- **Master loudness can overturn the premix.** The first intro became too loud after normalization.
  The final was remeasured at -31.5 dBFS intro and -44.7 dBFS outro.
- **Prefer motivated cuts over technical camouflage.** The final has straight cuts only and
  0.5-second outer fades; no crop, stitch or transition conceals failed sync or anatomy.
- **Put content in manifests.** Personas, lines, visible characters, gaze, environment and layout
  live in series/sequence/prompt-policy data. Generic code enforces schema and invariants.
- **Retain evidence, not preview sprawl.** Keep paid sources, accepted references, prompts, ledger,
  final timeline/master/manifest, final QA and decisions; prune recomputable samples and drafts.
- **Persist sound masters, not component clutter.** Keep the final ambience amalgamation and its
  script/provenance; discard individual background-voice and noise stems after mix verification.

Next: run one contrasting sequence with the same gate and add at most one bounded feature. Build a
reusable ambience mixer from independent speech assets. Objective lip-sync scoring may support but
never replace normal-speed human review. Alternative models require current provider, control,
licence and cost verification against a named failure before registry admission.

## Full-sequence voice-persona postmortem — 2026-08-03

The 43-second `clinic-full-sequence-20260803T184456Z` review artifact is not the contrasting accepted
run. It demonstrated a good one-card transfer and preserved the intended clinic/picture continuity,
but normal-speed review exposed two hard failures: the male patient sounds female and visible speech
is out of sync.

- **A voice must be inherited, not selected in a request.** The run's fresh `personas.json` has no
  voice object. `am_michael` and `af_sarah` appear only in TTS provenance, with no audition reference,
  perceived-gender/timbre decision, version lock or human casting approval.
- **Schema capability is useless when a run bypasses it.** `series/surrey-care/series.json` already
  owns structured voices, but the ad-hoc fresh cast did not inherit that series manifest. A run that
  cannot resolve every speaker to one canonical persona version and voice realization must fail
  before TTS or motion generation.
- **Provider or alias names are not perceptual evidence.** A label that suggests a male or female
  voice does not establish what a listener hears. Audition the rendered sample and record a human
  decision for age, timbre, gender presentation, accent, diction, pace and dramatic suitability.
- **Text accuracy is orthogonal.** ASR recovered the lines, but cannot prove speaker identity,
  casting, timbre or lip sync.
- **Audio integrity is orthogonal.** The high PCM PSNR only shows that the provider returned the
  supplied audio. It cannot show whether generated lips followed it.
- **Five fps is too sparse for sync acceptance.** Samples are 200 ms apart—more than twice the
  80 ms target. Review every utterance at normal speed with sound and inspect timecoded phonetic
  closures; add an objective offset/confidence result when local tooling is available.
- **Human playback is the final authority.** If a reviewer sees persistent lead/lag or hears the
  wrong voice, reject the take even when every automated technical check passes.

The next run may start only after both personas have approved, hashed voice auditions and the local
M5 Pro workflow can emit real audiovisual sync evidence. Do not spend on motion while either gate is
missing.

## Dynamic voice casting and bounded-retention update — 2026-08-03

- **The persona owns vocal intent; the provider catalog supplies replaceable realizations.** Rank the
  current catalog from explicit age, gender presentation, accent priority, timbre and vocal manner.
  Never use a character's appearance, name, ethnicity or cultural background as a voice-matching
  feature.
- **Ranking is a shortlist, not casting.** The deterministic matcher ranked alternatives, but the
  human deliberately selected reassuring Sarah for Maya and older, gentler Bill for Kenji. That
  override is valid and is recorded separately from the provider-neutral persona.
- **A voice preview does not approve a dramatic performance.** The selected provider voices are
  planned realizations until the exact six-turn performance passes the eight-part human voice gate.
  No motion request may inherit casting approval as performance approval.
- **Generate dialogue before fixing shot duration.** The first timestamped candidate is 26.16 seconds
  and uses 577 ElevenLabs credits. Bill's symptom turn is 6.24 seconds, so a passing performance would
  receive a seven-second dialogue shot instead of being clipped or unnaturally accelerated into the
  old five-second estimate.
- **One candidate, then listen.** Do not spend on a second dialogue performance or any video until the
  first candidate is reviewed at normal speed.
- **Delete rejected pixels, not production knowledge.** Large failed/rejected media may be pruned only
  from an explicit decision manifest containing its relative path, exact hash, rejection reason and
  retained evidence. Keep lessons, prompts, QA, manifests, ledgers, hashes and approved visual anchors.

## Maya and Kenji Cosmos/Wan production retrospective — 2026-08-03

The 47.459-second `clinic-cosmos-final-v02` render is a completed review candidate, not a human-
accepted final. It retains the Asian man/Black woman clinic anchor, binds Sarah and Bill through
versioned voice personas, uses Cosmos for the one-card handoff, and uses Wan picture performances for
the six spoken beats. Independent ASR recovered every intended word from audited windows of the final
master, including the then-scripted `BC Service Card`, `may be billed`, `Oh no`, `Doctors of BC`, and `after your visit`. The shareability repair corrects the official product name to `BC Services Card` and requires the replacement line and card prop to pass together.

- **Cosmos is excellent at the job it actually passed.** The face-free handoff preserved one card,
  ownership, contact, release, the empty withdrawing hand, reader geometry and clinic space. Two
  actor-visible silent Cosmos attempts retained identity and room geometry but made Kenji articulate
  inaudible speech. Stop after the bounded repair and use Cosmos for spatial inserts, not silent
  conversational faces, until that motion prior can be controlled.
- **Wan preserved the supplied audio extremely well.** Six initial takes retained identity, camera,
  clinic continuity and supplied audio at zero lag. The pilot measured 0.999806 correlation; the five
  final local synchronized clips measured 0.999826–0.999972 after AAC decode.
- **Provider turn timestamps are not edit points.** ElevenLabs' final reported boundary was 0.615
  seconds early, while several starts also contained the preceding speaker. That created duplicated
  fragments and clipped final words before Wan generation. The splitter now aligns the exact script
  against independent ASR word timestamps and cuts only inside inter-line gaps. The last turn owns the
  remaining candidate audio.
- **A content transcript can diagnose the pipeline, not perceived sync.** Whole-mix Whisper
  hallucinated filler in long ambience gaps, but speech-only windows from the exact final master
  recovered the complete canonical script. Waveform and ASR evidence prove content preservation;
  normal-speed human playback still decides voice performance and visible lip sync.
- **Use motivated picture coverage for an audio-boundary repair.** The coverage line needed 0.536
  seconds more mouth-motion lead than its retained Wan take provided. The final edit lets that line
  begin over the uninterrupted end of the Cosmos handoff, then cuts to Maya when her retained mouth
  performance starts. This preserves the card action and avoids a visible technical stitch.
- **Long provider jobs require an async return path.** Synchronous Cosmos requests disconnected near
  60 seconds despite a longer client timeout. The bounded webhook path completed both Cosmos and Wan
  calls without duplicate submission. Raw callbacks are data-URL duplicates and should be reduced to
  compact receipts immediately after the decoded media is hashed.
- **Do not use a public asset tunnel when direct bounded transport is unavailable.** A safer inline
  attempt was rejected by Wan's upstream 61,440-character field limit. The run stopped cloud
  generation and finished from retained local picture/audio rather than re-exposing repaired assets.
- **Budget reporting needs two numbers.** Provider-reported known actual is US$5.75976488. Nine
  unresolved requests reserve a conservative additional US$1.31, so the run remains below the
  authorized US$10 even under the worst-case ledger assumption.

Next: the user should review the 480p copy at normal speed with headphones, focusing on the last word
of Maya's greeting, the handoff-to-coverage cut, Kenji's disappointed `Oh no`, and the complete final
answer. If one sync defect is visible, repair that named interval only; do not reopen model selection.

## Shareability repair v03 — 2026-08-03

The 35.459-second `clinic-cosmos-final-v03` candidate repairs the five defects found during human
review of v02 without reopening the passing cast, clinic, or dialogue performances. It is still a
review candidate until normal-speed human playback with sound passes.

- **A static plate is not an establishing shot.** V03 opens directly on Maya's moving greeting. All
  24 sampled frames in the first second are unique, and the edit contains no freeze holds.
- **Room tone and room life are different assets.** The synthetic noise bed was replaced with a
  three-voice ElevenLabs background exchange, then filtered, spatialized, reflected and mixed as
  distant clinic activity. The final ASR hears only two brief background lines during the face-free
  handoff, rather than a continuous foreground conversation.
- **Picture duration must follow audible performance.** Every speaking shot now ends 80–225 ms after
  its independently detected final word. Long silent articulation is removed editorially; no actor
  shot is padded with a freeze or independently retimed audio.
- **Exact institutional names are content locks.** Sarah's replacement line is `May I see your BC
  Services Card, please?` and its new Wan take was generated from the replacement audio. Do not repair
  a changed spoken line by swapping only the soundtrack under an old mouth performance.
- **A required identity prop needs controlled source pixels.** The blank card was replaced by a
  fictional `SAMPLE` prop composited from the official Province of British Columbia Photo BC Services
  Card layout. Cosmos then animated the face-free handoff and preserved one card through contact,
  release and final ownership. No real identifier is present.
- **Spend against named defects.** The repair used exactly one Wan dialogue attempt and one Cosmos
  handoff attempt. New provider-reported video cost is US$0.749996; the final ASR has a conservative
  US$0.01 reservation because its response omitted cost. ElevenLabs reports 301 credits for the kept
  line and background dialogue. A discarded Sound Effects response omitted billing provenance, so
  220 credits remain reserved rather than being guessed away.

The automated gate passes exact wording, opening motion, frame geometry, codec, duration, final
loudness, no-freeze policy, card source lineage and ASR content. Promotion remains blocked on the
user's normal-speed audiovisual review. Independently, the card blip, slow handoff and absent living
wide coverage are retained as Stage 3 design debt rather than minimized as accepted limitations.

## Stage 2 strategic closeout and Stage 3 decision — 2026-08-04

Human review of v03 found three remaining production defects: a transient card-surface blip, a
handoff whose movement is too slow, and no living wide establishing/master coverage. These do not
justify another scene-specific clinic repair. They reveal missing general capabilities:

- exact high-information prop pixels must be tracked and composited independently from generated
  motion;
- essential action requires storyboarded onset, contact, release and completion time windows;
- a static anchor cannot substitute for an animated geography master or later return to shared
  space.

Stage 2 is therefore closed strategically with declared debt. Its strict two-sequence exit gate was
not met, and v03 remains a review candidate rather than an accepted final. The decision is explicit
so later work cannot silently rewrite that history.

The closeout is also a major positive milestone: the engine produced roughly one minute of coherent,
concluded two-character dialogue in a convincing clinic environment, with persona-bound voices,
realistic multi-voice ambience, bounded spend and traceable assembly. The remaining defects are the
next craft frontier, not evidence that the end-to-end production failed.

Stage 3 prioritizes cinematic craft rather than model accumulation. Its complete craft model covers
dramaturgy, character/relationship/plot arcs, intertwined theme threads, narrative viewpoint and
time, screenplay/dialogue/narration, directing and acting, mise-en-scene, cinematography and
lighting, storyboarding/previs, editing, sound/music/silence, VFX/compositing, colour/finishing,
continuity, production management, rights and ethics.

The immediate order is: a complete 5–12+ minute multi-set pilot with independently motivated A/B/C
plots; locked episode animatic and living coverage grammar; directing and performance; editing and
sound; production design and cinematography; then temporal action and exact props. The clinic becomes
a regression fixture rather than a genre template. A contrasting second-project preproduction
packet proves that core schemas and workflows transfer across tone, form and production state.

`gpt-5.6-sol` is the planned primary model for story architecture, screenwriting, preproduction
synthesis and difficult reviews once the user exposes OpenAI API access. DeepInfra remains a bounded
secondary evaluation/fallback lane and a remote media gateway. Cosmos3-Super is remote-only through
DeepInfra or a verified NVIDIA-hosted endpoint; it is never a local dependency. At stage start,
midpoint and closeout, a dated official-source web scan compares current LLM and multimodal
candidates on the same filmmaking evaluation packet. No model changes automatically.

See [the Stage 2 closeout](STAGE-2-CLOSEOUT.md) and
[the Stage 3 cinematic-series plan](STAGE-3-CINEMATIC-SERIES-PLAN.md).
