# Production vocabulary

Status: normative for Stage 2 planning, generation, editing, filenames, manifests and audits.
Existing completed-run artifacts remain immutable legacy evidence; new records must use these terms
and map any provider-specific vocabulary to them.

Run directories use the singular `edit/` for retained intermediate edit clips. The plural
`edits/` is not part of the Stage 2 layout; migrate any legacy contents before cleanup so two
competing folders cannot silently hold different versions.

## Working hierarchy

Narrative hierarchy: `Series → Season → Episode → Sequence → Scene → Beat`

Production/edit lineage: `Scene + beat plan → Setup → Take → Clip/source interval → Shot → Cut or transition → next shot`

Series through beat describe story organization and canon. Setup and take describe production. A
clip is media. A shot, cut and transition describe the edited result. Keeping those layers separate
prevents a generated file, camera plan and final screen interval from all being called a “shot” or
“scene.”

## Core terms

| Term | Standard definition | Boundary or usage rule |
|---|---|---|
| **Production** | The complete body of planned and generated work for one deliverable or test program. | May contain one or more sequences and their shared continuity state. |
| **Series** | The entire continuing show: its premise, world, enduring style, character canon and body of episodes. | Owns the series bible, style bible, canonical personas and long-range continuity. |
| **Season** | An ordered production and story block of episodes within a series. | Often released roughly yearly, but a season is not defined by a calendar year. It owns the season arc and season-start continuity state. |
| **Episode** | One standalone delivered installment or story within a season. | May contain one or more sequences and scenes while also advancing season or series arcs. |
| **Sequence** | A continuous narrative or thematic unit made from one or more related scenes. | May span locations or times while pursuing one dramatic purpose. Stage 2 currently plans, generates and accepts at sequence level. |
| **Scene** | Continuous dramatic action in one primary time and place. | A material change of time or primary environment starts a new scene. A new camera angle, setup or cut does not. |
| **Beat** | The smallest meaningful change in action, information, intention or emotion. | Several beats may occur in one shot; a beat does not require a cut. |
| **Setup** | One specific camera and production arrangement: position, height, angle, lens intent, framing, movement, lighting, axis and actor/prop blocking. | A material camera, lens, lighting or blocking change creates a new setup. Setup is a plan, not media. |
| **Frame** | One individual image in a video stream at one instant. | A frame is not a shot and does not describe shot size. Use **framing** or **shot-size class** for composition. |
| **Framing** | The intentional placement and scale of subjects, objects and negative space within the image. | Records composition, headroom, look-room and exclusions; it is part of a setup and may be evaluated throughout a shot. |
| **Shot-size class** | The project's top-level scale taxonomy: `wide`, `medium` or `close`. | Every planned Stage 2 shot declares exactly one class. More specific labels remain descriptive variants within that class. |
| **Wide shot** | Coverage in which geography, environment or full-body spatial relationships dominate. | Includes establishing and master views when their primary job is spatial context. |
| **Medium shot** | Coverage balancing a subject's performance or action with enough body and environment to preserve context. | This is the broad middle class; waist-up, medium-wide, medium two-shot and medium close-up are descriptive variants. |
| **Close shot** | Coverage in which a face, object or detailed action dominates and wider geography becomes secondary. | Includes a close-up and an insert such as the card transfer; it still requires safe edges, legibility and stable motion. |
| **Take** | One uninterrupted recording or generation attempt for one setup, from start to stop. | Each provider result is one take even when it is synthesized. A retry or new seed creates another take. |
| **Clip** | A discrete encoded media asset or file containing video, audio or both. | A raw clip may contain a complete take; an edit clip may be derived from one or more source intervals. “Clip” never names a narrative unit. |
| **Source interval** | A bounded `[in, out)` time range selected from a clip. | Always record clip ID plus source in/out timecodes. Trimming selects an interval; it does not create a new take. |
| **Shot** | One continuous image interval as experienced in the edit, from one cut or outer boundary to the next. | A shot normally uses one source interval. It may use multiple intervals only through an explicitly recorded, imperceptible stitch. |
| **Cut** | The exact frame or timeline instant where one shot ends and another begins with an immediate visual change. | “Cut” means the transition point, not the whole rendered version. Use **edit version** for a rough or final assembly. |
| **Transition** | The visual and/or audible method that connects adjacent shots or the sequence boundary. | Includes a hard cut, dissolve, wipe, fade-in and fade-out. A fade is a transition, not a cut. |
| **Stitch** | A technical join between source intervals intended to appear as one continuous shot. | Must be imperceptible. If the join is meant to be noticed, it is an editorial transition, not a stitch. |
| **Handle** | Extra source material retained before the selected in-point or after the out-point. | Preserve enough handles to review and adjust cuts without regenerating. |
| **Edit version** | A named assembly state of a sequence, such as rough assembly, review version or accepted version. | Do not use bare “cut” to mean a version. If an industry label such as “rough cut” is used, also provide a stable version ID. |
| **Delivery master** | The accepted rendered media file exported from the approved edit version. | Distinct from a **master shot**, which is coverage, and from a camera-original clip. |

## Character and persona terms

| Term | Standard definition | Ownership and change rule |
|---|---|---|
| **Character** | A narrative identity who can recur across episodes, seasons or the full series. | Has one stable `character_id` in the series bible. |
| **Canonical persona** | The series-owned creative specification for a character: identity, age baseline, cultural/community background, local history, language history, accent, voice, appearance, manner, worldview, backstory, relationships and durable behavior. | Inherited by every lower level. Never silently rewritten in a sequence, scene, setup, prompt or take. |
| **Persona version** | An immutable, identified revision of the canonical persona. | A deliberate canon change creates a new version with reason, effective episode and continuity approval; it does not overwrite prior episodes. |
| **Character reference pack** | The approved visual, voice and performance references used to realize a persona consistently. | Owned and versioned with the persona. Generated takes may use the pack but may not redefine it. |
| **Season character state** | The character's inherited condition and arc state at the start of a season. | May add season-specific goals, relationships or appearance state without contradicting the canonical persona. |
| **Episode character state** | The inherited state entering an episode plus explicit episode-local changes. | Records what changes during the episode and what is carried forward. |
| **Performance directive** | Beat-, scene-, setup- or take-specific instruction for emotion, intention, energy, gaze, pace or action. | Directs a performance without changing canonical identity, voice, accent or backstory. |
| **Casting realization** | The approved face/body/voice realization selected to portray the persona. | Must remain tied to the persona version and reference pack; a recast or voice change is explicit, reviewed and effective-dated. |

Persona control follows this inheritance rule:

`Series canonical persona → season character state → episode character state → sequence/scene performance directives → setup/take realization`

Lower levels may add context and performance state. They may not silently change higher-level canon.
A character's appearance, cultural background, language history, accent, base voice and durable
manner belong to the series persona; wardrobe for a particular day, current emotion, injury,
knowledge and immediate objective belong to episode/sequence/scene state as appropriate.

## Coverage and sound terms

| Term | Standard definition |
|---|---|
| **Coverage** | The set of complementary setups, takes and resulting shots available to edit a scene or beat. |
| **Master shot** | A shot designed to establish or preserve the scene's geography and principal action, commonly but not always wide. |
| **Insert** | A close shot of a story-relevant detail or action, such as the BC Services Card handoff. |
| **Reaction shot** | A shot whose primary story purpose is a character's response rather than a new action or line. |
| **Ambience bed** | Continuous, location-specific background sound that establishes the acoustic environment beneath the sequence. |
| **Foley** | Synchronized sound created or selected for a visible physical action, such as a card slide, cough or footsteps. |
| **Dialogue stem** | The isolated dialogue track or bus before it is mixed with ambience, foley or music. |
| **Off-screen dialogue** | Dialogue heard while the speaker's mouth is outside the frame. It may play over an insert or listener reaction and is not evaluated as visible lip sync for that shot. |
| **Sound mix** | The combined, level-balanced dialogue, ambience, foley and optional music used by an edit version or delivery master. |

## Generation and acceptance terms

| Term | Standard definition |
|---|---|
| **Generation request** | One provider call with a fixed model, prompt, seed, parameters, reservation and request ID. |
| **Candidate take** | A generated take awaiting admission review. It is not accepted merely because the request succeeded technically. |
| **Accepted take** | A take that passes source-level technical, composition, performance, continuity and safety gates for possible editorial use. |
| **Rejected take** | A retained or recorded take that failed admission; it must never silently re-enter an edit. |
| **Shot admission** | The decision that a specific source interval can realize a planned shot in an edit. Acceptance of a take does not automatically admit every interval from it. |
| **Sequence acceptance** | Final approval of the assembled sequence after picture, story action, continuity, lip sync, sound, transitions and evidence gates pass. |

## Required identifiers for new Stage 2 records

| Record | Preferred example |
|---|---|
| Series | `ser01` |
| Season | `ssn01` |
| Episode | `ep01` |
| Sequence | `seq01` |
| Scene | `scn01` |
| Setup | `set01` |
| Take | `take01` |
| Clip | `clip01` |
| Shot | `shot01` |
| Cut | `cut01` |
| Edit version | `edit-v01` |

IDs are scoped by their parent record in manifests. A timeline entry must preserve the chain from
series, season and episode through sequence, scene, setup, persona version/casting realization,
generation request, take, clip, source interval, shot and adjacent cut/transition. Existing IDs such
as `c07` remain valid only as legacy aliases and should be mapped to the new typed IDs when a
completed run is analyzed.

The SQLite `events.sequence` field is a legacy event-order counter, not a narrative sequence. Refer
to it in prose as the **event ordinal**; new schemas should use an unambiguous field such as
`event_index` or `event_ordinal`.

## Usage examples

- “Generate `take03` for `set02`” means another attempt without changing the camera setup.
- “Create `set03`” means the camera, lens, light or blocking plan materially changes.
- “Select `clip08` from 00:01.200 to 00:04.800 for `shot05`” identifies the exact source interval.
- “Place `cut04` between `shot04` and `shot05`” identifies an immediate editorial transition.
- “Stitch two intervals inside `shot06`” means the join must remain invisible and be separately
  audited. If it cannot be invisible, use a motivated cut to a new shot.
- The clinic card moment is one **beat** within a clinic **scene** inside a broader healthcare-cost
  **sequence**, which could be part of one **episode**, **season** and **series**. Its wide counter
  view and card insert are different **setups** and **shots**.

Avoid phrases such as “generate a scene” when the provider actually returns one take/clip, “new
take” when the camera setup changed, or “final cut” when the intended meaning is the delivery master.
