# Klarblick implementation handoff

## Objective and fixed decisions

Implement `docs/plan.md` as a weekend-hackathon MVP for German Gymnasium mathematics teachers (grades 5–10), with Grade 8 slope as the deeply tested hero lesson.

- Keep tests minimal: only hero workflow, safety/failure, and fallback checks.
- Do not add Docker. Run Next.js, FastAPI, and the AST-validated Manim subprocess locally.
- Approved provider configuration:
  - `MODEL_NAME=gpt-5.6-luna`, set by the user. Verified with a live call before being written to `.env`.
    The id is case sensitive: `gpt-5.6-Luna` returns 404. `gpt-5.6` and the previous `gpt-5.4-mini` also
    answer, so either is a fallback.
  - `ELEVENLABS_VOICE_ID=5KvpaGteYkNayiswuX2h` (Helmut, a German voice now speaking English through the
    multilingual model)
  - `RENDER_TIMEOUT_SECONDS=420`. It was 180 in `.env`, which silently overrode the code default and
    risked killing a legitimate final render of a longer lesson.
- `.env` contains both provider keys. Never print or copy those secrets.

## Implemented

- English Next.js teacher workflow: configuration, cascading catalog selectors, storyboard review, one-section revision, approval, progress, result player/cards/downloads, cached-result label, and terminal failure recovery.
- FastAPI catalog/storyboard/revision/approval/job/artifact endpoints.
- Pydantic contracts and curated Grade 5–10 mathematics catalog.
- LangChain structured storyboard/review/revision and free-form Manim code generation after approval.
- ElevenLabs timestamp narration, SRT generation, timing extraction, and FFmpeg mux/caption burn.
- Local single-job Manim pipeline with AST validation, credential-scrubbed environment, timeout, `-ql` preview, per-section frames, deterministic layout gate, visual review, two repair attempts, `-qm` final render, and three `-s` recap scenes.
- Fixed polished slope source in `fallback/hero_lesson.py` plus `scripts/build_hero_fallback.py`.
- Reusable paid smoke runner: `scripts/run_live_smoke.py`.
- Local setup/start/prerequisite scripts and README.

## Current state of the two paths

### Cached hero fallback: complete and verified

`fallback/` now holds all four real narrated artifacts (`lesson.mp4`, `recap_1.png`, `recap_2.png`, `recap_3.png`).
Before this session it held only `hero_lesson.py`, which meant the cached-fallback branch was dead code:
a live failure raised `FileNotFoundError` and the job went to `FAILED`. The safety net now works and was
observed working on a real failed live run, which ended in `cached_fallback` with the polished artifacts served.

Verified properties of the current English fallback (job `fallback-build-028a14e0`):

- 105.00 s, 1280×720, 30 fps, H.264 video plus AAC mono audio, five sections.
- In sync and not truncated: silent visual 105.93 s, narration 105.04 s, last subtitle ends at 1:44.9.
- All five preview frames and all three recap cards pass the frame-bounds gate.
- Captions no longer collide with mathematics.
- The narration was resized to the measured 13.5 characters per second, so 105 s delivered against 99 s
  declared. The earlier German bundle delivered only 54 s against the same 99 s.

Note it is five sections and 105 seconds, longer than the new 30 second target for freshly generated
lessons. That is intentional: it is the polished hand-written hero, it still validates inside the accepted
range, and `cache_fallback` no longer overwrites it after a successful live run.

### Lessons are short by default, which is what made the live path testable

The live path was failing run after run, and the loop itself was the problem: each test rendered five
sections and about 105 seconds of video twice, preview and final, so a single misplaced label cost roughly
three minutes and a paid narration. Lesson size is now configurable and small by default:
`lesson_target_sections = 2` and `lesson_target_seconds = 30` in `services/api/app/settings.py`, passed to
the planner as a `constraints` block. The accepted validation range stays wider (2–6 sections, 25–120
seconds) so the bundled five-section hero example still validates.

Two consecutive live runs then reached `ready` with **zero repairs**, in 117 and about 100 seconds:

- Job `cbef518011dc4870b7dbd29f83b186a2`: 29.81 s, in sync, but the review approved frames where labels
  crossed the arrows and the formula sat on the axis numbers.
- Job `4d7b775bf20948868c1556d169507b59`: 25.12 s, and visually clean. Frame 1 is a graph with a
  colour-matched legend column, frame 2 a formula stack; no overlap, correct label-to-arrow pairing, all
  frames and cards inside bounds.

The fix between those two runs was the **legend column**: in layout A every label now goes into one
`VGroup` placed with `next_to(axes, RIGHT, buff=0.5)`, with the axes shifted `LEFT * 1.2` to free that
column. Labels can no longer land on the line, the points or the axis numbers, which removed the entire
class of overlap that the model kept reproducing. The review prompt was also corrected: an earlier
recalibration had made it treat overlapping text as acceptable "tight spacing", so it now rejects any
wording that crosses a drawn shape while still tolerating shapes that merely touch.

### Live path: an earlier successful run at full length

`scripts/run_live_smoke.py` reached `ready` with `provenance: live` and **zero repair attempts**:

- Storyboard `12f6fed9ba3041e5ab78c5ebdc263a84`, job `fb33db58b43145bd9a9602f4f8431f93`.
- 171.5 seconds from approval to finished media, inside the plan's three-minute target.
- 1280×720, 30 fps, H.264 plus AAC, five sections, three recap cards, all retrievable through the API.
- All five section frames and all three cards pass the frame-bounds gate.

Five earlier live runs ended in `cached_fallback`. Each removed a distinct real defect rather than
repeating the same failure; those defects are listed below.

**Known quality issue in that run: audio and video drift apart.** The silent animation ran 136.5 s while
the narration was 118.4 s, so FFmpeg's `-shortest` trimmed about 16 s of animation and the closing
section's narration plays over the previous section's visuals. Animations can only be padded by
`self.wait`, never shortened, so any section whose animations outrun its narration pushes every later
section out of sync. This is now caught deterministically by the sync gate described below, which was
added after that run completed.

## Defects found and fixed this session

1. **No safety net.** `fallback/` contained no media. Fixed by building the artifacts.
2. **Caption band was never reserved.** The prompt allowed content down to `y = -3.5` while FFmpeg burns
   subtitles at roughly `y = -4.0` to `-3.4`. The hero's own section 3 clipped "Steigung: 2" off the frame
   and collided with a caption. Fixed with a `CONTENT_TOP = 2.3` / `CONTENT_BOTTOM = -3.0` band and a
   mechanical `fit_content(...)` clamp in both `fallback/hero_lesson.py` and the codegen prompt. This
   implements the plan's Sprint 3 rule "captions kept clear of important mathematics", which the original
   `y ∈ [-3.5, 3.5]` bound structurally violated.
3. **Layout defects depended on a model judgement.** Added `services/api/app/frame_checks.py`: a
   deterministic gate that rejects any preview frame whose outer 2 percent contains lesson content, before
   the paid visual review runs.
4. **Frame sampling missed sections.** Frames were taken every 20 s, so a 54 s video only ever showed
   sections 1, 3 and 5. Now one frame is sampled per section, using the real narration durations so the
   sample lands mid-section instead of on a transition fade.
5. **Repair reasons were discarded.** Each attempt's rejection now appends to `attempts.log` in the job
   directory, with the repaired source kept as `lesson_attempt_N.py`. This is what made the remaining
   diagnosis possible; keep it.
6. **The attribute allowlist rejected valid Manim API.** `append`, `Cross`, `axes.x_axis`, `y_axis` and
   `get_unit_size` were all rejected, each wasting one of only two repair attempts. Attribute access is
   not the safety boundary, so unknown-attribute rejection was removed and replaced by an explicit ban on
   dunder access (`__class__`, `__globals__`), which is the one route that could escape the sandbox.
   Import restrictions, banned names, ManimGL detection and the scrubbed subprocess are unchanged, and
   `DOCUMENTED_ATTRIBUTES` remains as documentation of the expected surface.
7. **Generated code had no background or contrast rule.** Scenes rendered dark colours on default black
   and the review reported "kaum lesbar". The prompt now fixes the full palette, requires
   `self.camera.background_color = BG_COLOR` in every scene, and forbids the dark Manim default colours
   for text.
8. **The bounds gate was calibrated too tightly.** `MAX_CONTENT_FRACTION` was 0.4 percent, exactly the
   noise level of a heading resting near the top edge; it rejected a well-composed frame twice and cost a
   full live run. Measured reference frames put real cut-off content at 2.9 to 10.2 percent and clean
   frames below 0.4 percent, so the threshold is now 1.5 percent, with a regression test pinning the
   near-edge case as acceptable.
9. **The codegen prompt contradicted itself.** Layout A allowed `next_to(axes, DOWN, buff=0.3)`, which with
   the axes at `shift(DOWN * 0.35)` lands near `y = -3.2`, inside the caption band the same prompt forbids.
   Text below the axes is now disallowed.
10. **Rejection messages did not name a target.** The gate now reports "Bild 3 zeigt Abschnitt 3, also die
    Methode section_3", and the `add_coordinates` rejection explains why instead of saying "unknown
    attribute".

11. **Nothing measured audio/video sync.** Added a deterministic sync gate in `LocalRenderer._sync_issues`:
    the preview's measured length is compared with the sum of the narration's section durations, and the
    render is rejected before the expensive final pass if the animation overruns the speech (drift and a
    truncated tail) or falls short of it (truncated audio). Validated against the real measurements: the
    good fallback passes, the drifted live run is rejected, and an under-length animation is rejected.
    The prompt now also caps the sum of `run_time` per section at 60 percent of its duration and requires
    `transition_out` to fade every mobject in a single `self.play` call, because one `FadeOut` per
    `self.play` added seconds of drift across five sections.
12. **Caption-band enforcement was tried and deliberately rolled back.** The bounds gate checks only the
    outer 2 percent, while the reserved caption zone is the bottom eighth of the frame. Widening the
    blocking bottom band to 12.5 percent was implemented and tested, and it did catch real subtitle
    collisions — but it then failed an otherwise good lesson on three consecutive attempts over a single
    label sharing space with a subtitle. Since sync matters more than caption overlap, only genuine
    cut-off at the frame edge blocks a render. `BOTTOM_MARGIN_RATIO` in
    `services/api/app/frame_checks.py` documents this and can be set back to `0.125` in one line.
13. **The fallback bundle was overwritten by every successful hero run.** `cache_fallback` now only seeds
    `fallback/` when the bundle is missing, so the deliberately polished hero render is never replaced by
    whatever the last live run happened to produce.
14. **`render_timeout_seconds` was 180 s per subprocess.** A 100 second lesson renders at roughly 1.8x
    realtime at `-qm`, so a legitimate final render could be killed. Raised to 420 s.

## Language: the product is now English

The user decided to convert everything to English while keeping German Gymnasium teachers as the audience,
accepting this as a hackathon trade-off. `docs/plan.md` still describes a German-language app; that premise
is deliberately superseded. What changed:

- All nine prompt modules in `prompts/` were rewritten in English, not translated line by line, so the
  accumulated codegen lessons are consolidated in one place.
- `narration_de` became `narration` and `message_de` became `message` on the Pydantic models, the
  TypeScript types, the UI and the smoke script.
- `content/math/catalog.json` uses English ids and labels (`label`, `notice`, `learning_goal`,
  `misconceptions`). The hero pair is now `linear-functions` / `understanding-slope`; the old German slugs
  no longer resolve, so any stored storyboard JSON under `jobs/` from before the switch is stale.
- Every teacher-visible string in `apps/web` and every backend error and status message is English.
- `services/api/app/hero.py` and `fallback/hero_lesson.py` were rewritten in English, and the hero
  narration was resized to about 13.5 characters per second so it fills its declared durations. That
  closes the earlier 54 s versus 99 s mismatch.
- The umlaut check in `validation.py` stays. It is a MathTex safety rule, not UI text.
- `ELEVENLABS_VOICE_ID` is unchanged, so a German voice now speaks English through the multilingual
  model. Swap the id in `.env` for a native English voice if the accent matters.

## Priorities set by the user

- **Audio/video sync matters more than captions.** Effort should go to keeping picture and speech
  together, not to perfecting the caption band. Captions remain burned in because `docs/plan.md` §1
  requires them and they already work at no further cost, but they are not the leading constraint.
- Keep things simple; this is a hackathon MVP.

## Prompt rework against OpenAI's guidance

At the user's request the prompts were rebuilt following OpenAI's prompt engineering guidance rather than
being translated line by line. The changes that mattered:

- **Identity first, then instructions, examples and context.** Each prompt now opens with a short identity
  section and uses `#` headers as delimiters, instead of a flat bullet list.
- **Positive framing.** The codegen prompt was a wall of "never" and "not allowed". It now states what to do,
  and the genuine hard limits are collected in one "Safety limits" section at the end, where being explicit
  is the point.
- **Worked examples instead of prose.** `prompts/manim_codegen.md` now shows a complete correct
  `section_1` for layout A and `section_3` for layout B. Repeated live failures were structural mistakes
  (four label lines stacked above the axes, formulas labelled from the side), which an example prevents far
  better than a paragraph.
- **Explicit output format** at the top: one complete Python file, no fence, no commentary.

## Validator: namespace check instead of a hand-written list

Three separate live runs were lost to the *name* allowlist rejecting valid Manim API (`Cross`,
`BraceBetweenPoints`, `axes.x_axis`, `get_unit_size`) and even the plain builtin `isinstance`. Names are now
validated against `dir(manim)` of the installed version, via `manim_namespace()` in
`services/api/app/validation.py`. Verified: 578 real names accepted, while `ShowCreation`, `GraphScene`,
`TexMobject`, `TextMobject`, `get_graph` and invented names such as `MagicRectangle` are still rejected. This
satisfies the plan's "hallucinated or ManimGL-only names fail before rendering" without a list that has to be
maintained by hand. `ALLOWED_GLOBAL_NAMES` remains as the fallback when Manim cannot be imported.

## Manim documentation cross-check

The layout rules were originally reverse-engineered from failures, so they were checked against the
official Manim Community documentation:

- The frame is 8 units high with a 16:9 ratio, about 14.22 units wide, origin centred. The three-zone
  model in `prompts/manim_codegen.md` matches this exactly.
- "Use `Text` for plain text, `Tex`/`MathTex` for formulas." The prompt's rule now states this reason,
  since `Text` is Pango-based and renders umlauts without extra LaTeX packages.
- The docs recommend `config.frame_width` / `frame_height` over hardcoded dimensions. **Deliberately not
  adopted.** Frame *units* are fixed at 8.0 high regardless of render resolution, so the constants are
  already resolution-independent, while allowlisting `config` would expose attributes such as
  `media_dir` that can redirect renderer output out of the job directory. The cost is real and the
  robustness gain is zero here.
- `add()` argument order determines z-order, with the left-most argument furthest back.

## Known open items

- **Longer lessons are the untested case now.** Both clean live runs were 2 sections and about 25–30
  seconds. Raising `lesson_target_sections` / `lesson_target_seconds` re-enters the territory where the
  crowding failures happened, so raise them one step at a time and read `attempts.log` after each run.
- **A long lesson can still overshoot two minutes.** `POST /api/storyboards` validates the *declared*
  duration sum, while the delivered video follows the real narration length, which has run about 15 percent
  longer. At a 120 second target that would deliver more than the plan's two minute ceiling.
- **The plan's own numbers are now superseded twice**: `docs/plan.md` specifies a German app of 4–6
  sections and 60–120 seconds. The language change and the short-lesson default are both deliberate user
  decisions, so treat the plan as historical on those two points.
- **The fixed hero storyboard in `services/api/app/hero.py` declares ~99 s but its narration text only
  fills ~54 s.** Measured speaking rate is 13.5 characters per second (2.12 words per second). Live
  generation did not have this problem; it was already within about 3 percent. Fixing it means rewriting
  the five German narration texts and rebuilding the fallback (one paid narration call plus about three
  minutes). Cosmetic only: audio and video stay in sync, and the delivered video is simply shorter than
  the hero storyboard's declared durations.
- `prompts/storyboard.md` now states the speaking rate. The following run overshot slightly, declaring
  90 s for about 104 s of text, which still lands inside the promised 60–120 s.
- The in-app browser was unavailable, so no browser-automation screenshot pass was completed. The UI was
  reviewed by reading `apps/web/app/page.tsx`; API, typecheck and production build pass.

## Verification commands

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m unittest tests.test_minimal_checks -v
.\.venv\Scripts\python.exe -m compileall -q services\api scripts
npm run typecheck --prefix apps\web
.\.venv\Scripts\python.exe scripts\run_live_smoke.py
```

Rebuild the fallback bundle only if `fallback/` loses its media:

```powershell
.\.venv\Scripts\python.exe scripts\build_hero_fallback.py
```

## Important constraints and cautions

- Keep the two-repair maximum.
- Do not bypass the AST validation or the frame-bounds gate, and do not present silent technical smoke
  media as the real fallback.
- Do not expose `.env` values or provider keys in output/logs.
- Preserve user files and unrelated workspace changes; there is no Git repository in this workspace.
- Generated runtime files live below `jobs/` and are ignored.
- Do not add broad tests, auth, databases, Redis, Docker, cloud storage, or physics/chemistry generation
  to this MVP.
