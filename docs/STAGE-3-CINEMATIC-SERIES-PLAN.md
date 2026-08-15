# Stage 3 plan: cinematic grammar and versatile series production

Date: 2026-08-04
Status: planned; no installation, model download or live generation is authorized by this document

## North star

Build a low-budget engine capable of varied cinematic projects and recurring dramatic series with:

- short-form drama's story density, controlled-set economics and reusable project-scoped production
  assets without hardcoding one genre, location, voice or tone;
- prestige-streaming discipline in composition, blocking, lighting, performance, editing and sound;
- austere naturalism rather than glossy advertising: motivated available light, unvarnished faces,
  observational proximity, sparse production design and emotionally specific behaviour;
- provider-independent production truth, local-first generation where it is technically credible,
  and cloud models reserved for shots whose accepted value exceeds their cost.

“Netflix-level” is a craft north star, not a claim of platform certification or a promise that one
model can currently produce a finished premium episode. Stage 3 proves the repeatable filmmaking
disciplines that can close that gap.

## Quality ladder

| Level | What the viewer experiences | Stage 3 position |
|---|---|---|
| AI demo | Attractive isolated clips, visible artifacts, weak geography and inconsistent sound | Must be left behind |
| Efficient short-form drama | Immediate story, clear coverage, fast production and emotionally readable performances | Minimum floor |
| Premium short-form series | Stable cast/world, authored shot grammar, controlled action, convincing sound and no shareability defects | Stage 3 target |
| Prestige-streaming drama | Subtext-rich performances, expressive mise-en-scène, sophisticated blocking, coherent season language and invisible technique | Long-term north star |

## Project-aware production architecture

The engine is not a clinic generator or even only a series generator. Its root hierarchy is:

`Portfolio → Project → Production → narrative form → Sequence → Scene → Beat`

A project may be a series, feature, short, anthology, documentary, commercial experiment or another
declared form. Its manifest owns `project_id`, form, genre, tone, audience contract, runtime target,
aspect ratio, frame rate, narrative mode, craft priorities, visual/sound bible, model policy, budget
policy and lifecycle state. The narrative branch beneath it adapts to the form: for example,
`Series → Season → Episode`, `Feature → Act`, or `Anthology → Installment`.

Every project has its own namespace for personas, casting realizations, sets/locations, hero props,
style rules, continuity, accepted assets, cost ledger and model decisions. Core engine code may reuse
schemas and craft methods, but it may not inherit clinic characters, institutional language, visual
tone or location defaults. The clinic becomes a regression fixture for dialogue, voices, ambience,
physical action and exact surfaces.

Production state is explicit: `development`, `writing`, `greenlight`, `preproduction`, `production`,
`postproduction`, `review`, `accepted`, `delivered` or `archived`. Each gate records accepted assets,
unresolved debt, continuity state, forecast/actual spend and the exact creative/model decisions that
produced the next state.

## Complete cinematic craft model

The engine treats cinema as an interdependent set of crafts. It must represent the intention,
decisions, evidence and review of each craft without pretending they can be reduced to one score.

### Story architecture and dramaturgy

- Series premise, dramatic engine, genre promise and audience contract.
- Season, episode, sequence, scene and beat structure.
- Main plot, character plots and secondary plots, including where they intersect or deliberately
  remain apart.
- Character want, need, wound, contradiction, stakes, choices, reversals and consequences.
- Character arcs across episode and season, including relationships that change both participants.
- Theme and counter-theme expressed through choices, images and consequences rather than speeches.
- Setups, payoffs, withheld information, reveals, dramatic irony and audience knowledge.

The series bible should carry `theme_threads`, `plot_threads`, `character_arcs`, relationship arcs
and planned intersections. Each scene declares which threads it advances, complicates, echoes or
resolves. A scene that advances none of them needs a compelling atmosphere or character reason to
remain.

### Narrative viewpoint, voice and time

The engine distinguishes who tells, who knows and what the camera/editor allows the audience to
know:

- **First person:** a character recounts or experiences events through voice-over, diary, testimony,
  memory or strongly subjective audiovisual treatment. First-person narration does not require every
  image to be a literal optical point-of-view shot.
- **Second person:** a motivated address to “you”—another character, an absent person, the audience
  or the speaker's past/future self. It is a deliberate dramatic device, not a required checkbox.
- **Third-person limited:** the scene stays emotionally or informationally close to one focal
  character even when the camera is externally observable.
- **Third-person objective:** the audience sees behaviour without privileged access to private
  thought.
- **Third-person omniscient:** narration or editing can move across characters, places and knowledge
  boundaries.
- **Unreliable narration:** picture, sound, performance or later evidence may contradict the teller;
  the contradiction and reveal schedule must be planned.
- **Temporal form:** linear action, flashback, flash-forward, memory, ellipsis, parallel action and
  repeated events from another viewpoint require explicit time and knowledge state.

Planned records should include `narrative_mode`, `focal_character_id`, `knowledge_boundary`,
`narrator_character_id`, `voiceover_status`, `reliability`, `temporal_order` and `reveal_ids`.

### Screenwriting and dialogue

- Scene objective, obstacle, tactic, escalation, turn and exit value.
- Dialogue intention, subtext, status, rhythm, interruption, silence and what remains unsaid.
- Distinct character diction, sentence length, vocabulary, humour, avoidance patterns and language
  history inherited from the persona.
- Exposition distributed through conflict and behaviour rather than informational speeches.
- Narration that adds a second meaning, compresses time or controls viewpoint rather than describing
  visible action.
- Read-aloud timing and actor breath before storyboards or shot duration are locked.

### Directing and the actor's art

- Casting realization and persona continuity.
- Given circumstances, private stakes, moment-before, objective, obstacle, playable action and
  beat-to-beat tactic changes.
- Listening and reaction as performance, not dead time between generated lines.
- Blocking, proximity, touch, gaze, posture, tempo, stillness and use of props.
- Performance continuity across setups generated out of order.
- Restraint, ambiguity and subtext over generic “sad,” “happy” or “cinematic” expressions.

Prompts should use playable direction—“reassure him while hiding that she expects conflict”—rather
than asking for an abstract emotion. Human review judges whether the performance communicates the
intended action and change.

### Mise-en-scène and production design

- Location architecture, social meaning, geography and practical use.
- Set dressing, props, screens, documents and exact-content surfaces.
- Costume, hair, makeup, age continuity and material wear.
- Actor placement, background ensemble, foreground layers, depth and negative space.
- Palette, texture, weather, season, time of day and recurring visual motifs.
- Production economy through reusable locations, wardrobe states and hero props.

### Cinematography and lighting

- Viewpoint and camera placement before lens ornament.
- Shot size, lens intent, subject distance, camera height, angle, axis, headroom and look room.
- Static, handheld, pan, tilt, dolly, track, crane or zoom only when motivated by story attention.
- Key, fill, contrast, practical sources, exposure, colour temperature and face readability.
- Depth of field, shutter/motion character, texture and grain as part of the series language.
- Shot-to-shot lighting, screen direction, scale and movement continuity.

### Storyboarding, previs and coverage design

- Beat boards, floor plans, axis and eyeline maps.
- Storyboards that show staging and editorial intention rather than attractive unrelated frames.
- Animatics with real dialogue timing, ambience, action clocks, handles and proposed cuts.
- Coverage matrices that protect geography, performance, action, reactions and editorial options.
- Contingency coverage for the highest-risk generated action or exact-content beat.

### Editing and temporal composition

- Selection for performance first, then continuity and technical polish.
- Cuts motivated by thought, gaze, movement, action, sound, reveal, contrast or deliberate rupture.
- Scene tempo, internal rhythm, breathing room, ellipsis, montage and duration of reaction.
- Parallel action, point-of-view structure and control of audience knowledge.
- J-cuts, L-cuts, sound bridges and off-screen space.
- Invisible technical stitches distinguished from expressive editorial transitions.

### Sound, music and silence

- Dialogue recording/synthesis, perspective, room match and intelligibility.
- Ambience, background ensemble, foley and designed effects with spatial depth.
- Music theme, motif, instrumentation, entrance/exit and relationship to dialogue.
- Silence as tension, intimacy, shock or absence—not missing production value.
- Narration perspective and acoustic placement distinguished from scene dialogue.
- Final mix, dynamics and playback translation across headphones and ordinary speakers.

### VFX, generative integration and compositing

- Exact surfaces, screens, cards and titles composited deterministically.
- Tracking, rotoscoping, masks, clean plates, stabilization and temporal consistency.
- Generative extension used for environment, motion and treatment without surrendering exact content.
- Effects serve story invisibly unless the effect itself is the subject.

### Colour, finishing and delivery

- Shot matching before stylized grading.
- Exposure, skin tone, palette, highlight/shadow behaviour and intentional texture.
- Denoise, grain, upscale and sharpening applied conservatively and audited in motion.
- Titles, subtitles, captions, credits and safe areas remain deterministic.
- Review copy, delivery master, stems, captions, manifest and provenance exported reproducibly.

### Continuity, production management and ethics

- Script supervision across character state, wardrobe, props, geography, light, time and performance.
- Rights and licence records for models, voices, music, source references and recurring assets.
- Privacy, representation, consent and no misleading use of real identities or documents.
- Schedule, disk, memory, cost and accepted-asset reuse.
- Clear authorship and human approval at story, casting, performance and final acceptance gates.

## Priorities

The engine should eventually represent every dimension above, but Stage 3 cannot improve them all at
once. Priority is based on audience impact, current weakness, reusability and cost of learning.

### Priority 0 — hard gates on every sequence

- coherent story event and understandable dramatic turn;
- persona, voice, exact-content, safety and rights compliance;
- intelligible dialogue and no perceptible visible-speech failure;
- stable geography, character, prop and sound continuity;
- technically valid, reproducible delivery and honest acceptance status.

### Priority 1 — Stage 3 craft focus

1. **Story and scene intention:** objective, obstacle, reversal, character consequence and one
   declared theme/plot-thread contribution.
2. **Episode architecture:** independently motivated A/B/C character plots, meaningful
   intersections, controlled information flow and a satisfying convergence or counterpoint.
3. **Previsualized film grammar:** locked animatic, living wide/master, shared geography, motivated
   reactions and action clock.
4. **Directing and performance:** playable objectives, listening, subtext, voice continuity and
   restrained beat changes.
5. **Editing and sound:** cuts on dramatic events, correct pace, semantic ambience, synchronized
   foley, silence and two-device mix review.
6. **Mise-en-scène and cinematography:** functional locations, intentional blocking, motivated
   camera/lens/light and consistent palette.
7. **Temporal action and exact props:** natural motion timing plus deterministic tracked surfaces.

Local-model benchmarking supports these priorities; it is not itself a cinematic achievement.

### Priority 2 — introduce after the vertical slice passes

- recurring visual and musical motifs;
- one controlled narrative-viewpoint device, such as first-person voice-over or third-person limited
  audiovisual subjectivity;
- deeper theme/counter-theme and plot-thread intersections;
- expressive but bounded camera movement;
- shot matching and a reusable colour pipeline;
- local VFX/compositing automation beyond the exact-prop prototype.

### Priority 3 — Stage 4 and later

- season-scale character and relationship arcs beyond the pilot episode;
- nonlinear, omniscient, unreliable or second-person narration when dramatically justified;
- original score system and episode-level sound motifs;
- multi-location continuity, day/night progression and complex transitions;
- sophisticated VFX, titles and full delivery packages.

This ordering prevents breadth from becoming superficial checkbox work. The Stage 3 episode is
planned completely before generation, then earned sequence by sequence. Its vertical slice must
already feel like one piece of an authored ensemble story, not three unrelated demonstrations.

## Scope

Stage 3 produces one complete **5–12+ minute multi-set ensemble pilot**. The final runtime is selected
only after the screenplay, animatic and cost forecast make the accepted-value tradeoff visible:

- **Core:** 5–6 minutes when funds or local throughput are tight;
- **Standard:** 8–10 minutes for a fuller plot weave;
- **Expanded:** 12+ minutes only when the animatic proves every scene earns its duration and the user
  separately approves the forecast.

The pilot targets three to five sets, four to seven speaking characters and three plot threads:

- **A plot:** the episode's principal dramatic spine and strongest causal pressure;
- **B plot:** a different character's independent want, obstacles and consequential turn;
- **C plot:** a compact but complete counterpoint, complication or emotional echo.

No subplot exists merely to deliver information to A. Each has its own protagonist/focal character,
objective, escalation, turn and changed exit state. Intersections must create causality, obstruction,
revelation, ironic contrast, thematic echo or final convergence. “Interwoven like Seinfeld” means
this general ensemble construction, not imitation of a living artist's dialogue or surface style.

Before full production, make one **60–90 second multi-set vertical slice** containing at least two
sets, two plot threads, a living wide, one dialogue exchange, one reaction and one motivated sound or
picture bridge. It is a go/no-go checkpoint, not a separate story. The complete episode is first
locked as a beat matrix whose rows are scenes/time and whose columns track A/B/C pressure through
cold open, inciting events, escalation, midpoint collision, complications, convergence and tag/coda.

Stage 3 also completes a no-generation preproduction packet for a second, deliberately contrasting
project/genre/tone. That packet proves schema portability without doubling video spend.

## The production method

### 1. Write for production value

- Build the episode's A/B/C beat matrix before polishing individual scenes. Every scene changes at
  least one plot, character/relationship arc, theme or audience-knowledge state.
- Give each scene one principal dramatic question, one consequential turn and one visually playable
  action; enter late, leave on changed value and avoid resetting character state between sequences.
- Prefer a legible ensemble and reusable authored sets over crowd spectacle. Give B and C plots
  independent wants and full turns rather than treating their characters as delivery devices.
- Use recurring locations, wardrobe and props as series assets, not prompt text recreated each run.
- Separate exact institutional/legal wording from improv-friendly performance language before TTS.

### 2. Lock an animatic before video generation

The animatic contains approved stills, temporary or final persona voices, ambience, shot duration,
action timecodes, cut points and the complete dramatic rhythm. It must answer:

- what changes in every beat;
- why each cut occurs;
- what the wide proves;
- where the audience should look;
- when an action begins, contacts, releases and completes;
- which lines may play off screen;
- what sound carries each transition.

No paid or heavyweight local video request begins until the animatic passes story clarity, coverage
and duration review.

### 3. Generate coverage by setup, not by dialogue line

Every scene plans a coverage matrix before generation:

| Coverage job | Minimum expectation |
|---|---|
| Living establishing/master | Native landscape, readable geography and purposeful motion; never a still plate |
| Medium two-shot | Both principals share space and blocking; usable before and after the dramatic turn |
| Speaker/listener coverage | Complementary eyelines, safe mouths, matched environment and reaction handles |
| Essential insert | One story-critical detail or action, short and temporally specified |
| Reaction | Silent, closed-mouth emotional consequence with usable pre/post handles |
| Return to space | A wider shot after the key change, action or decision unless intentionally waived in the storyboard |

Repeated profile talking heads should not dominate the timeline. As a starting target, at least 25%
of accepted picture time should preserve shared geography through wide or medium two-shot coverage;
the exact ratio remains an editorial decision.

### 4. Make wides living shots

- A geography master normally lasts 2–5 seconds in the edit and contains purposeful activity: an
  entrance, approach, task, body turn, exchanged look, passing staff member, changing practical
  light or restrained motivated camera movement.
- The source take preserves enough duration to cover the complete beat even if the edit uses less.
- A cold open may delay the establishing view, but the storyboard must state why and establish
  geography within the first dramatic unit.
- A static anchor remains valuable for identity and layout conditioning, but it cannot be admitted
  directly as finished motion coverage.

### 5. Give physical action a clock

Every essential action declares intended time windows before generation. A short handoff might use:

| State | Example target |
|---|---:|
| Initiation | 0.00–0.35 s |
| Approach | 0.35–0.85 s |
| Stable shared contact | 0.85–1.15 s |
| Release | 1.15–1.45 s |
| Completion and reaction handle | 1.45–2.25 s |

Prompts, reference motion and audits inherit these windows. The engine measures observed state
boundaries and blocks a take whose pace is materially slower than the animatic. For face-free,
non-dialogue action only, a bounded whole-picture-and-foley speed change may be considered and must
be re-audited; visible dialogue is never independently retimed to rescue an action.

### 6. Separate motion from exact surfaces

Printed cards, screens, labels, documents and recurring logos follow an exact-content pipeline:

1. generate or capture a clean action plate with stable prop shape and visible corner geometry;
2. track the prop plane locally with optical flow or feature tracking;
3. apply the approved exact surface through a frame-level homography;
4. restore hand/finger occlusion with a reviewed mask;
5. reject corner drift, surface flicker, topology change or identity loss at normal speed;
6. retain the source plate, track, masks, surface asset, composited clip and hashes.

The video model creates motion, light interaction and physical context. It does not invent exact
high-information pixels.

### 7. Treat sound as half the scene

- Preserve one persona-owned performance master per recurring speaker whenever practical.
- Build separate dialogue, ambience, foley and optional music stems.
- Use location-specific ensemble chatter, not principal lines or synthetic noise beds.
- Time foley to contact frames and use sound bridges to motivate picture cuts.
- Review on headphones, ordinary laptop/phone speakers and at the final encoded loudness.
- Keep a silent reaction when silence has dramatic purpose; do not fill every gap automatically.

## Runtime and model strategy

Model names are replaceable implementation details. Exact IDs, licences, prices, memory use and
verification dates must be refreshed before installation or live use.

### Reasoning and orchestration

Use OpenAI `gpt-5.6-sol` through the Responses API as the planned primary creative brain. Use `max`
reasoning for stage reviews, project/episode architecture, A/B/C plot interweaving, final screenplay
synthesis and difficult root-cause analysis. Start scene plans, script-doctor passes, continuity and
storyboard reviews at `xhigh`, then lower effort only when the fixed evaluation packet shows no loss.
Standard mode is the default; Pro mode is an independently benchmarked option, not an automatic
setting. OpenAI API authentication is intentionally deferred until the user later exposes a key, and
no paid request is authorized by this plan.

This selection follows OpenAI's current official guidance: `gpt-5.6` aliases to the flagship
`gpt-5.6-sol`, the Responses API is preferred for reasoning/tool workflows, and the model supports
reasoning efforts through `max`. Text reasoning remains cheap relative to accepted video seconds,
but tokens, latency and quality are still measured:
[OpenAI GPT-5.6 guidance](https://developers.openai.com/api/docs/guides/latest-model),
[GPT-5.6 Sol model](https://developers.openai.com/api/docs/models/gpt-5.6-sol).

DeepInfra is a bounded secondary lane for independent evaluation, fallback and models that win a
stage-specific packet. It is also a known remote media gateway. Qwen remains historical Stage 1/2
evidence and a possible local/private utility, not the Stage 3 creative primary. Deterministic
parsing, schema checks, budgets and acceptance gates remain code-owned rather than delegated to any
LLM.

LM Studio remains useful for local LLM/VLM fallbacks, private checks and orchestration. Its official
documentation describes running large language models and local inference APIs, not a video
diffusion runtime, so video weights should not be forced into LM Studio merely to keep one UI:
[LM Studio documentation](https://lmstudio.ai/docs/app/basics).

### Mandatory stage-review model scan

At stage start, at the mid-stage spend/go-no-go gate and at closeout, scan the live web as of that
date. Use official model/API documentation and model cards first. Save the result under
`research/model-candidates/YYYY-MM-DD-stageN.json` with:

- verification timestamp, exact model ID, provider/API surface and stable/preview lifecycle;
- configured-access status without exposing a credential;
- current input/output pricing, free/trial limits, context/output limits and likely latency class;
- reasoning modes, structured outputs, tools and relevant text/image/video understanding;
- data-handling, licence and production-use constraints relevant to the project;
- intended filmmaking role and result on the same versioned evaluation packet.

The fixed packet covers: project premise/theme architecture; independent A/B/C plot design and
intersections; a 5–12 minute beat matrix; subtextual scene/dialogue rewrite; storyboard and coverage
plan; cross-scene continuity audit; and evidence-based postmortem. Score anonymized outputs for
dramaturgy, character specificity, production feasibility, continuity, instruction adherence,
originality and cost/latency. A scan may recommend an experiment, but only the human owner/main
agent can promote a new primary. Never switch on brand reputation, vendor benchmarks or a mutable
`latest` alias alone; pin the exact tested model/version where the provider permits it.

The initial Stage 3 scan is recorded in
`research/model-candidates/2026-08-04-stage3.json`. It makes GPT-5.6 Sol the primary and retains
current Anthropic, Google and DeepInfra models only as unconfigured or secondary candidates until
they pass this production-specific packet.

### Local video candidate: LTX 2.3

The first Apple Silicon benchmark candidate is LTX 2.3 through its official local pipeline, LTX
Desktop or ComfyUI. The official model is a 22B joint audio-video model with image-to-video,
video-to-video and control adapters; its weights use the LTX community licence. LTX Desktop reports
local Apple Silicon operation with at least 15 GB free RAM, and the model card documents MPS use:
[LTX Desktop](https://github.com/Lightricks/LTX-Desktop),
[LTX 2.3 model card](https://huggingface.co/Lightricks/LTX-2.3).

This is a candidate, not an assumed winner. Benchmark it at 480p with short frame counts before any
720p production claim. Record peak unified memory, swap, generation time, thermal behaviour, output
quality, accepted seconds and exact local/cloud text-encoding boundary. Review the community model
licence before production use.

### Local workflow host: ComfyUI

ComfyUI officially supports Apple Silicon through MPS and provides built-in LTX nodes. Use an
isolated project-specific environment, pinned workflow JSON, reviewed custom nodes, read-only model
weights and a narrowly writable run directory:
[ComfyUI macOS documentation](https://docs.comfy.org/installation/desktop/macos).

### Wan

Do not assume 64 GB of unified Mac memory is equivalent to 80 GB of CUDA VRAM. Wan's official 14B
I2V and speech-to-video instructions state an 80 GB GPU requirement; its TI2V 5B path states 24 GB
VRAM but does not establish an official Apple Silicon production path. Therefore:

- retain DeepInfra Wan 2.6 only for bounded, audio-conditioned visible dialogue while it continues
  to pass quality and price checks;
- treat local Wan 2.2 TI2V 5B as an isolated feasibility experiment only after disk, licence,
  community-node provenance and MPS compatibility review;
- do not download or designate the 14B models as local production dependencies without measured
  evidence: [official Wan 2.2 repository](https://github.com/Wan-Video/Wan2.2).

### NVIDIA Cosmos

Cosmos3-Super is a 64B world model whose official local path targets Linux and NVIDIA Ampere,
Hopper or Blackwell hardware and discusses multi-GPU sharding. It is not a credible local M5 Pro
baseline. **Local execution is prohibited for this project.** Keep it as a remote specialist for
spatial causality, physical action and world-state continuity—not visible dialogue or exact printed
surfaces. DeepInfra is the known current route; its live page lists `nvidia/Cosmos3-Super` at
US$0.05/second for 720p, with 480p at half that rate, but price and endpoint support must be refreshed
before every reservation:
[DeepInfra Cosmos3-Super](https://deepinfra.com/nvidia/Cosmos3-Super),
[official NVIDIA Cosmos repository](https://github.com/NVIDIA/cosmos).

NVIDIA-hosted NIM/API Catalog access is a discovery candidate because the NVIDIA Developer Program
advertises free hosted endpoints for prototyping. Do not infer that the exact Cosmos3-Super
Generator endpoint is currently hosted, available to this account, free, licensed for delivery or
sufficiently stable. At each stage review, verify the exact endpoint, remaining allowance, rate
limits, retention/privacy terms and production-use rights before considering it. Otherwise use the
bounded DeepInfra route:
[NVIDIA NIM for developers](https://developer.nvidia.com/nim).

### One-model residency on the Mac

Only one heavyweight model family may be resident at a time:

1. persist current run state and release the active model;
2. verify sufficient free unified memory and no unexpected swap pressure;
3. load the next pinned model/workflow;
4. generate sequentially into the scoped run directory;
5. record model hash, runtime version, memory peak and elapsed time;
6. unload before starting LM Studio, another video runtime or an upscale pass.

## Continuous cinematic craft improvement

Technical reliability and cinematic craft use related but separate loops. Hard failures block a
take; craft scores explain how the next production should improve.

### Per-sequence improvement loop

1. **Refresh candidates when the stage gate is due:** perform the dated official-source model scan
   and retain the current primary unless a fixed-packet comparison justifies a reviewed change.
2. **Observe:** watch the previous accepted/rejected sequence at normal speed on two playback
   systems and record timecoded reactions before reading manifests.
3. **Diagnose:** separate story, coverage, performance, action, continuity, model and post-production
   root causes.
4. **Choose one craft hypothesis:** for example, “returning to the master after the cost reveal will
   make the power shift legible.”
5. **Build two animatic alternatives:** vary only the hypothesis-driving choice.
6. **Generate the minimum coverage needed:** reuse accepted locations, personas and setup recipes.
7. **Blind compare:** hide provider/model labels and compare the complete edits, not isolated clips.
8. **Promote or reject the pattern:** add a winning setup/edit/sound pattern to the project style
   bible only after it succeeds in two contrasting sequences.
9. **Update the benchmark reel:** retain accepted shots, known failure examples, scores, costs and
   reasons; delete reproducible large failed derivatives only under retention policy.

### Human craft scorecard

Score each dimension from 1–5 after hard gates pass:

| Dimension | Question |
|---|---|
| Dramaturgy | Does the scene advance a plot, character/relationship arc or theme through a consequential choice? |
| Story clarity | Can a first-time viewer understand the scene, stakes and turn without explanation? |
| Narrative viewpoint | Is the audience's knowledge and emotional alignment deliberate and consistent? |
| Dialogue and narration | Are voice, subtext, silence and any narration character-specific and dramatically additive? |
| Composition | Is every frame intentionally organized, with expressive use of space and scale? |
| Coverage grammar | Do wides, shared frames, singles, inserts and reactions form a coherent visual sentence? |
| Blocking and action | Do bodies and props move with intention, plausible tempo and readable completion? |
| Lighting and colour | Does light serve mood and faces while preserving the series palette and material texture? |
| Direction and performance | Do gaze, listening, silence, gesture, voice and timing express playable intention and subtext? |
| Production design | Do location, costume, props, background action and recurring motifs reveal this story world? |
| Editing rhythm | Do cuts occur on thought, action, gaze or sound, with no dead generated handles? |
| Sound world | Do dialogue, space, foley and silence create a convincing dramatic environment? |
| Continuity | Are character, wardrobe, geography, light, background state and props stable across cuts? |
| Emotional residue | Does the final image/sound leave the intended feeling after the information is delivered? |

The scorecard records reviewer, confidence and timecoded evidence. A total score cannot compensate
for a hard safety, exact-content, sync or continuity failure.

### Operational learning metrics

- provider and local compute cost per accepted second;
- generated seconds per accepted second;
- accepted-take rate and number of paid attempts;
- percentage of final duration using shared geography coverage;
- action-tempo error versus animatic target;
- exact-content defects per exact-content shot;
- continuity defects per cut;
- time from approved animatic to accepted sequence;
- craft-score delta versus the prior accepted sequence;
- number of reusable setup, location, persona, sound and post-production assets promoted.

## Stage 3 budgets

- No live request is authorized by this plan. OpenAI, DeepInfra, NVIDIA and ElevenLabs calls each
  require configured access and a user-approved episode/vertical-slice cap before transmission.
- Do not extrapolate the former short-scene budget to a 5–12 minute episode. First lock the screenplay
  and animatic, benchmark local accepted-seconds/hour and acceptance ratio, then forecast the core,
  standard and expanded runtime options with low/expected/high provider cost.
- Text-reasoning spend is tracked separately and optimized after creative quality; video remains the
  dominant scarce resource. Reuse cached project/series context when the API's measured economics
  support it.
- Use local generation for exploration and coverage variants once its benchmark passes.
- Use remote video only for named hero, dialogue, action or continuity defects that the local lane
  cannot meet. Every request reserves verified current price and stops after two non-improving tries.
- Track ElevenLabs credits separately from US-dollar provider cost; never invent a conversion.
- The 60–90 second vertical slice is the financial go/no-go gate. Full-episode generation requires a
  fresh user-approved cap after its audit and cost-per-accepted-second forecast.

## Stage 3 implementation order

### Sprint 1 — preproduction and measurement, no generation

1. Add the machine-readable Stage 3 production plan, debt register and project manifest schema.
2. Run the dated model-candidate scan and version the filmmaking evaluation packet.
3. Develop the pilot premise, theme/counter-theme, ensemble personas and independent A/B/C arcs.
4. Lock the episode beat matrix, screenplay, set plan and full dialogue/performance master.
5. Add animatic, coverage-matrix, action-clock and craft-scorecard schemas.
6. Add validators for living-wide coverage, return-to-master intent and exact action time windows.
7. Add an accepted-shot benchmark index and timecoded failure taxonomy.
8. Complete the contrasting second-project preproduction packet to test portability.

### Sprint 2 — local runtime benchmark

1. Inspect free disk and unified-memory headroom.
2. Review LTX code/model licence, installer provenance, telemetry and local/API boundaries.
3. Benchmark one 480p, 2–4 second living-wide clip with no real or private data.
4. Record cold/warm load time, peak memory, swap, generation time, stability and output quality.
5. Compare against one existing cloud result using the same acceptance packet.

Installation and large model downloads require a separate explicit approval after the disk and
licence review.

### Sprint 3 — exact-prop and temporal-action prototype

1. Generate or reuse one face-free neutral-prop action plate.
2. Implement local quadrilateral tracking, homography, occlusion masks and flicker checks.
3. Compare the deterministic composite with the v03 card handoff at normal speed.
4. Promote the method only if the exact surface and action tempo both pass.

### Sprint 4 — multi-set vertical slice

Produce 60–90 seconds from the locked pilot with at least two sets and two intersecting plot threads,
a living master, shared-frame blocking, listener reactions, full sound stems and a blind Stage 2
quality-floor comparison. Do not use the clinic script again merely because its assets are
convenient; the slice must test portability and episode assembly.

### Sprint 5 — episode production and post

After the vertical slice passes and the user approves the forecast, produce the episode sequence by
sequence. Re-audit story/continuity, budget and the model scan at the midpoint. Lock picture only
after A/B/C causality, performance continuity, location geography, exact surfaces and the complete
sound world pass normal-speed human review.

## Exit gate

Stage 3 completes after one accepted 5–12+ minute, multi-set episode and one contrasting
no-generation project packet pass all applicable gates, and:

- A, B and C each have an independent objective, escalation, turn and changed exit state;
- their intersections are causally or thematically meaningful and the final convergence/counterpoint
  is legible without explanation;
- every scene has required living geography, motivated coverage and continuity with adjacent scenes;
- no final exact-content surface flickers, mutates or becomes unreadable;
- essential action timing stays within the storyboarded tolerance and feels natural at normal speed;
- recurring personas, voices, location state and episode continuity remain stable;
- all visible dialogue receives human-approved sync and performance review;
- sound stems, foley and two-device listening decisions are retained;
- every produced sequence improves or preserves its declared craft dimension without regressing
  existing gates;
- median human craft score is at least 4/5, no dimension is below 3/5, and timecoded rationale is
  retained;
- the model scan exists for stage start, midpoint and closeout, and every primary-model decision has
  fixed-packet evidence;
- cost per accepted second and generation-to-acceptance ratio are reported across the episode;
- the accepted-shot library contains reusable wide, shared-frame, dialogue, action, reaction and
  transition patterns;
- no core schema or default prompt requires the clinic genre, location, characters, institution,
  dialogue tone or visual style; the contrasting project packet validates that separation.

## Roadmap after Stage 3

- **Stage 4 — Contrasting production:** a second complete 5–12 minute work in a materially different
  genre, tone, narrative mode and visual/sound language, exercising project isolation and portfolio
  orchestration.
- **Stage 5 — Repeatable season:** a small set of episodes sharing a series bible, location
  library, character arcs, visual grammar, sound motifs, asset retention rules and measured cost per
  finished minute.

Long duration is earned by repeatable accepted coverage. It is not achieved by asking a video model
for longer clips.
