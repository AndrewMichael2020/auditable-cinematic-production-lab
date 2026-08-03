# Stage retrospective: lessons and next steps

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
8. Retain the auditable core and prune only artifacts that can be reproduced from retained media.

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
- new TTS providers while the current synchronized speech is satisfactory;
- broad model comparisons without a specific failure the new model is meant to solve.

The stage gate is now **repeatable quality under a small budget**, not a larger feature surface.

## Clinic robustness result

The contrasting clinic test completed a 49.69-second, twelve-interval scene for US$2.625 actual
against US$3.075 reserved. The final, paid sources, rejected takes, dialogue edits, append-only
ledger, hashes, staged audits and timeline provenance are in `runs/clinic-20260803T011736Z/`.

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

Pareto next steps:

1. Add one small, licensed cough/foley library and a deterministic cue track; this run had a visual
   cough but no separate audible cough effect.
2. Preserve subtle motion in the final reaction rather than holding a still frame, but regenerate
   only when the ending is a story-critical performance beat.
3. Record exact internal edit boundaries at edit time. Hash-to-hash provenance is present here, but
   segment-level timecodes should be emitted automatically for every multi-segment repair.
4. Repeat one more contrasting location before adding dashboards, automated aesthetic scoring or
   more providers.
