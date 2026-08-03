# Clinic full-sequence voice-persona and lip-sync postmortem

## Decision

`runs/clinic-full-sequence-20260803T184456Z/` is a **rejected review artifact**. It is not a second
accepted Stage 2 sequence and must not be used as a voice, lip-sync or final-quality reference.

Generation is paused while work moves to an M5 Pro machine with 64 GB of memory. This is a workflow
handoff, not permission to resume generation automatically.

## What the run established

The run remains useful evidence for several bounded questions:

- the bright teal/light-maple clinic and fresh visual identities remain coherent enough across the
  edit;
- the silent Care Card beat shows one continuously visible card, patient ownership, shared contact,
  patient release and nurse placement on the separate reader;
- the edit uses motivated speaker/shot-size changes and avoids the earlier same-angle nurse cut;
- the 43-second review file decodes cleanly and the intended text is intelligible;
- paid requests stayed inside the shared US$8 authorization.

These successes do not compensate for a failed voice or lip-sync gate.

## Blocking findings

| Finding | Evidence | Decision |
|---|---|---|
| Male patient has a female-sounding voice | User normal-speed listening of the delivered sequence | Block |
| Voice is absent from the run persona | `personas.json` contains appearance, wardrobe, screen position and acting direction, but no voice object, voice realization, audition or reference hash | Block |
| Voice selection bypassed series canon | TTS aliases are recorded only in `provenance/new-dialogue-tts.json`; the run does not inherit `series/surrey-care/series.json` and directly used a different TTS path from the configured dialogue model | Block |
| Visible speech is perceptibly asynchronous | User normal-speed audiovisual review | Block |
| Prior sync QA was invalid | It used five-fps face sheets and PCM PSNR. Five fps samples every 200 ms; PSNR proves audio transport only. Neither can establish the 80 ms sync target | Block |
| ASR was overinterpreted | ASR recovered the words, but does not identify the correct actor voice, perceived gender/timbre or mouth timing | Block |

## Root-cause chain

1. The run generated new visual personas outside the canonical Stage 2 series persona manifest.
2. Those personas omitted voice entirely.
3. TTS voice aliases were chosen inside generation code and recorded after the fact in provenance.
4. No audition sample was reviewed and bound to the persona before motion generation.
5. No invariant connected a dialogue speaker to one approved `voice_realization_id`.
6. Source audio was sent to the I2V model, but no production-grade audio-to-viseme gate evaluated the
   result.
7. Sparse stills and intact audio were incorrectly promoted to a lip-sync pass.
8. The final normal-speed human review correctly rejected both voice casting and synchronization.

The principal failure is therefore not “a bad voice file.” It is missing production data and a
false acceptance method.

## Required voice-persona contract

Every speaking canonical persona must own:

- `character_id`, `persona_version` and stable `voice_realization_id`;
- written perceived age range, gender presentation, timbre/register and vocal manner;
- language history and respectful accent/diction direction;
- provider, model, exact voice/version and synthesis settings;
- an audition script that exercises ordinary speech, names/acronyms and emotional range needed by
  the sequence;
- retained audition audio and SHA-256;
- human approval for perceived age, gender presentation, timbre, accent, diction, pace, intelligibility
  and dramatic fit;
- effective date/version and an explicit recast path.

Every dialogue line and sequence-wide performance master must resolve to that exact voice
realization and audition hash. Missing or conflicting bindings fail before TTS, lip sync or I2V.

## Required lip-sync gate

For each visible utterance:

1. Review the complete source at normal speed with delivered sound.
2. Record timecoded utterance start/end, long pauses and representative closures/plosives.
3. Reject persistent audible lead/lag, mouth motion during silence, speech with a still mouth or
   incorrect closure timing.
4. Run an objective local offset/confidence tool when available and target absolute offset within
   80 ms.
5. Treat low-confidence objective output as unresolved, not a pass.
6. Preserve picture and audio together after admission; any independent shift or retime requires a
   new full review.

ASR, matching durations, shared trim transforms, audio hashes, PCM PSNR and contact sheets do not
replace this gate.

## M5 Pro 64 GB handoff

Before resuming:

1. Check out the reviewed PR/branch on the M5 Pro.
2. Transfer ignored `runs/` assets separately and verify retained source/final hashes. Do not move
   secrets through Git.
3. Install Python 3.11+, FFmpeg and the editable package; run the complete test suite and dry
   preflight.
4. Confirm the chosen local inference stack supports Apple Silicon/MPS, but do not generate motion.
5. Create one short offline audition for each canonical persona and retain the exact settings/hash.
6. Obtain explicit human approval of both auditions.
7. Implement/verify speaker-to-voice binding and fail-closed manifest validation.
8. Establish a normal-speed plus objective audiovisual-sync audit on a short disposable proof.
9. Only then authorize one bounded motion request under a new run cap.

## Cleanup performed

The artifact policy identified four intermediate QA contact sheets as deterministically
recomputable. `prune-artifacts --apply` removed them and reclaimed 2,897,721 bytes. The cleanup audit
is retained at `audits/artifact-prune.json` in the ignored run folder. Paid sources, original/padded
dialogue, the review MP4, Care Card action evidence, final contact/cut evidence, prompts, provenance
and budget records were preserved fail-closed.

## Restart acceptance criteria

The next sequence cannot be accepted unless all of these are true:

- each principal has an approved voice persona and immutable voice realization;
- the delivered voice perceptually matches that casting across all lines;
- every visible utterance passes normal-speed sync review;
- objective offset evidence is retained when available and any unresolved result blocks;
- the Care Card, environment, composition, identity, edit, sound and technical gates also pass;
- no hard failure is reported as a “known limitation” or overridden by successful billing/provenance.
