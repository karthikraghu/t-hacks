# Subject packs: mathematics and physics — design notes

`docs/plan.md` puts other subjects outside the MVP and closes with the intended route in: *future
subjects should be added through new subject packs, catalogs, teaching-method guidance, and
validation rules without changing the approved-storyboard and artifact pipeline.*

This document works out what a subject pack has to be, given the code as it now stands, and scopes
the work to **mathematics (the existing subject, restructured) and physics (the first new one)**.
Chemistry is deferred — see §9. Video creation only; the assignment feature has its own subject
question and is out of scope here.

**Status (2026-08-15):** All three stages are implemented. The physics hero subtopic has been
rendered live end to end (117 s: narration → codegen → one AST repair → preview → advisory review →
final render), producing a playable narrated MP4 and three recap cards, and the successful hero
render auto-seeded `fallback/physics/`. One known defect from the render-and-watch loop remains
open: on the two-line comparison frame the right-side secondary formulas overflow the frame edge
(logged by the advisory review). Tightening the physics Layout A legend rules against that render
is the next iteration; `scripts/build_hero_fallback.py` also still assumes the math hero.

## 1. The finding that shapes everything else

**Swapping the subject prose is trivial. Swapping the visual vocabulary is the whole project.**

`prompts/math.md` is nine lines. Writing `physics.md` is an afternoon.

`prompts/manim_codegen.md` is 234 lines, and roughly half of it is one subject's visual vocabulary
worked out against real renders: two named layouts, a `create_axes()` factory every section builds
from, and hand-tuned constants such as
`create_axes().scale(0.83).shift(DOWN * 0.35 + LEFT * 1.2)`. Those numbers exist because a render
was watched and corrected. A physics free-body diagram needs its own set of them, plus its own
entries in `prompts/visual_review.md`, and neither can be written correctly without rendering,
watching, and revising.

So the honest cost of a new subject is **one catalogue + one prose file + one layout vocabulary
proven against real renders**, and the third item dominates. Any plan that treats a subject as a
prompt swap will produce videos that validate, render, and look wrong.

### The layout vocabulary lives in two prompts, and they are a matched pair

This is easy to miss and would sink a naive pack format. The planner's `storyboard.md` permits
exactly two section shapes ("a coordinate system plus at most three labels" / "at most four short
lines of text or formulas"), and codegen's `manim_codegen.md` implements exactly those two as
Layout A and Layout B. The planner only plans what codegen can build; codegen only builds what the
planner plans.

A pack that adds a free-body layout to its codegen prose without also extending the planner's
permitted shapes will never get a free-body section planned. The reverse produces plans codegen
cannot realise. **A pack therefore declares each layout once, with a planner-facing half (what the
storyboard may ask for) and a codegen-facing half (how to build it), and the loader injects each
half into the right prompt.** Two files kept in lockstep by hand is the fallback; one declaration
split by the loader is the goal.

## 2. What already does not care about the subject

Audited against the current code. None of this needs to change:

| Component | Why it is already neutral |
|---|---|
| `services/api/app/rendering.py` | Runs Manim in a scrubbed subprocess; the scene is just Python |
| `services/api/app/narration.py` | ElevenLabs timing over whatever narration it is given |
| `services/api/app/frame_checks.py` | Purely geometric — background/content masks and edge bounds |
| `services/api/app/storage.py` | JSON job state, artifact paths |
| `services/api/app/validation.py` | Validates names against the **real installed Manim namespace** (`manim_namespace()`), not a maths list. Physics needs `Arrow`, `DoubleArrow`, `GrowArrow` — all already accepted |
| `services/api/app/catalog.py` | Reads any JSON shaped `grades[] → topics[] → subtopics[]`; nothing in it is arithmetic |
| `Level`, `TeachingMethod` in `models.py` | `support/standard/challenge` and `visual_linking/worked_example/error_analysis` are pedagogy, not mathematics |
| `prompts/shared_education.md`, `review.md`, `revision.md`, `repair.md` | Generic teaching and repair rules |

`pipeline.py` is *almost* neutral: its orchestration is subject-blind, but it seeds and serves the
fallback from a single flat `fallback/` directory via `catalog.is_hero()` (lines 145–162). Making
the fallback per-subject touches those lines. Small, but it is a pipeline change — the plan's
"without changing the pipeline" holds for the flow, not for every line.

## 3. What is mathematics-shaped today

Seven places, all of them narrow:

1. **`settings.catalog_path`** — a single file (`content/math/catalog.json`). One subject can exist
   at a time, and `main.py:36` builds one `Catalog` at import.
2. **`ai.py` loads `math.md` in three places** — `storyboard_prompt()` (line 73), the storyboard
   reviewer (line 106), and `revise_section` (line 130). Each is a literal filename. Note what is
   *not* on this list: `generate_code` (line 143) and `repair_code` (line 150) load only
   `manim_codegen.md` — subject prose never reaches codegen today. The pack's codegen-facing
   layout prose is a **new** injection at those two call sites, not a swap of an existing one.
3. **`prompts/manim_codegen.md`** — Layout A/B, the shared `create_axes()` factory, the
   slope-specific instruction under *Structure*, and the `MathTex`-centred rules under *Text and
   notation*.
4. **`prompts/storyboard.md`** — the two permitted section shapes (the planner half of the matched
   pair from §1).
5. **`prompts/methods.md`** — ends with "For slope, combine visual_linking and worked_example."
6. **`prompts/visual_review.md`** — reject rule 6 says "the mathematics shown contradicts the
   storyboard"; the examples reference axis labels and triangles.
7. **`hero.py` + `fallback/`** — the hero storyboard is **Python** (`hero_storyboard()` builds a
   `GeneratedStoryboard` in code), tests import it directly, and `pipeline.py` assumes one flat
   fallback bundle with hardcoded filenames.

## 4. Proposed shape of a subject pack

```text
content/<subject>/
  pack.json               identity, label, hero pointer
  catalog.json            grades → topics → subtopics (shape unchanged)
  subject.md              replaces math.md — the subject's own correctness rules
  layouts.md              the layout vocabulary: per layout, a planner-facing shape rule
                          and a codegen-facing build recipe (§1); the loader injects each
                          half into the right prompt
  methods.md              the per-subject `auto` guidance and method reinterpretations
  review.md               optional: extra reject rules for the frame reviewer
  hero_storyboard.json    the fallback storyboard as data, validated through the same
                          Pydantic models — packs carry no Python (§4, safety)
fallback/<subject>/       the rendered hero bundle (lesson.mp4, recap_1..3.png)
```

`content/math/` becomes the first pack: `prompts/math.md` → `content/math/subject.md`, the layout
half of `manim_codegen.md` + the section-shape rules of `storyboard.md` → `content/math/layouts.md`,
`hero.py`'s storyboard serialized to `content/math/hero_storyboard.json`, and `fallback/*` →
`fallback/math/`.

### Code changes this implies

- `LessonRequest` gains `subject_id: str = "math"`. **The default is load-bearing**: persisted
  storyboards and jobs under `jobs/` embed the old schema and must still deserialize. Explicit
  rather than inferred from `topic_id`, because two subjects will eventually both want a topic
  called `waves` or `functions`.
- The `grade: int = Field(ge=5, le=10)` bounds move out of `LessonRequest` and into per-pack
  catalogue validation. Physics starts around grade 7 and simply carries fewer grades; the model
  should not hardcode any subject's range.
- A `SubjectRegistry` replacing the single `Catalog`: loads every pack under `content/`, resolves
  `(subject_id, grade, topic_id, subtopic_id)`, exposes `is_hero()` and the pack's prose, and
  deserializes `hero_storyboard.json` where `hero.py` is imported today.
- `AIService.prompt("math.md")` becomes `pack.subject_prompt()` at the three planner-side call
  sites, **plus** the new codegen-side injection of the pack's layout prose at `generate_code` and
  `repair_code`.
- `pipeline.py` fallback seeding/serving takes the pack's `fallback/<subject>/` root instead of the
  flat directory.
- `GET /api/subjects` returns the pack list with each pack's catalogue. **`GET /api/catalog` stays
  as an alias for the math pack's catalogue** until the front-page doors and the lessons page are
  moved over — retiring it in the same change would break both.

### What a pack must *not* be allowed to do

`ALLOWED_IMPORT_ROOTS = {"manim", "numpy", "math"}` in `validation.py:9` is the safety boundary that
matters. **A pack must not be able to widen it from JSON**, or adding a subject becomes an
escalation path into arbitrary imports inside the render subprocess. Any new import root stays a
code change with a human reading it. Same for `BANNED_NAMES` and `BANNED_ATTRIBUTES`, and the same
reasoning is why the hero storyboard is JSON, not Python: packs are data, loudly and completely.

## 5. Physics

**The first new subject, because it needs no new dependencies and reuses the layout that already
works.**

What it needs on screen:

- Time-axis graphs (v–t, s–t) — **the existing axes layout unchanged**, including the tuned
  `create_axes()` constants. A velocity–time graph and a linear-function graph are the same picture
  with different labels. These subtopics ship first.
- Labelled vector arrows — `Arrow`, `DoubleArrow`, `GrowArrow`, all in the validator's namespace
  already.
- A free-body diagram — a body shape plus arrows from a common point. The one genuinely **new**
  layout, declared in `layouts.md` with both halves (§1) and proven against real renders.
- Units in notation: `MathTex(r"a = 9{,}81\,\mathrm{m/s^2}")`, units spoken as words in the
  narration while the symbol appears on screen. A `subject.md` rule.
- An apparatus sketch (ramp, pendulum, circuit) — the weakest area. A crude ramp is `Line` +
  `Polygon`; a circuit is not realistically drawable well by a model without primitives.

Sensible opening catalogue: kinematics, forces, energy — graph-shaped subtopics first, because they
land on the proven layout. Electricity and optics wait until the free-body layout has earned trust.

**Risk:** a physics topic whose only honest picture is an apparatus will produce a weak video.
Mitigation is catalogue curation, not prompt engineering — ship the subtopics the layouts can
actually serve, exactly as the maths catalogue was curated.

Teaching methods transfer as-is; error analysis is arguably *stronger* in physics (sign and unit
errors) than in maths. The `TeachingMethod` enum stays closed — each pack's `methods.md`
reinterprets the three existing methods rather than adding new ones, because a closed enum is what
keeps the UI honest.

## 6. Where the subject appears in the UI

The front page is already two doors (`/lessons`, `/assignments`), so the subject belongs **inside**
the lessons tool, not as more doors — doors are per-user, and a physics lesson has the same user as
a maths lesson.

Add a `Subject` fieldset above `Grade` in `SetupStep`, in the same `.choice-row` style as the grade
pills. Changing subject loads that pack's catalogue and resets grade/topic/subtopic to its hero or
first entry — the existing `openingSelection()` logic, per pack. No new step in the rail: subject
is part of setting up.

If only one pack is installed, the fieldset does not render at all — which is also what makes the
UI shippable *before* the physics pack exists.

## 7. Staged plan

### Stage 0 — Build the seam, ship no new subject

`subject_id` (defaulting to `"math"`), the `SubjectRegistry`, the pack directory layout, the
two-prompt layout injection, the hero storyboard as JSON, and the per-subject fallback root — with
maths as the only pack.

**Done when:** the test suite passes with path-and-import updates only (tests hardcode
`content/math/catalog.json`, read `fallback/hero_lesson.py`, and import `hero_storyboard` — those
references move; no behavioural assertions change), the hero slope path renders identically, and
`content/math/` is a pack rather than a special case.

Worth doing on its own even if no second subject ever ships: it removes the three literal
`math.md` loads, the single-catalogue assumption, and the hero-in-Python special case.

### Stage 1 — Subject selection in the web client

The fieldset from §6, `GET /api/subjects`, and the `/api/catalog` alias. Ordered **before** the
physics pack deliberately: it is fully testable with one pack (the fieldset stays hidden), and it
means physics is reachable from the UI the day it works instead of only by API call.

**Done when:** a single-pack install looks exactly as it does today, and a second pack dropped into
`content/` appears as a choice with no client change.

### Stage 2 — Physics pack

Catalogue for grades 7–9 (kinematics, forces, energy), `subject.md`, `layouts.md` covering the
reused axes layout + vectors + the new free-body layout, `review.md` reject rules for mislabelled
vectors, `hero_storyboard.json`, and one hero subtopic rendered and bundled under
`fallback/physics/`.

**Done when:** a physics hero subtopic produces a playable narrated video and three recap cards on
the live path, selected through the UI, and the maths hero still does.

## 8. Open questions

1. **One hero per subject, or one per app?** Per subject costs a rendered fallback bundle each; the
   pack shape above assumes per subject. Confirm the disk/demo cost is acceptable.
2. **Free-body as the second layout, or something cheaper?** If the render-and-watch loop for
   free-body runs long, the physics pack can ship graph-subtopics-only first — the catalogue is the
   scope knob.
3. **How many packs at once?** The registry is trivial for a handful; if the answer is eventually
   "twenty", the catalogue-as-one-JSON-file assumption should be revisited then, not now.

## 9. Chemistry — deferred, and why

Manim has no chemistry primitives. The three routes were assessed: `chanim` (real structural
formulas, but a new import root across the §4 safety boundary, a `chemfig` LaTeX install, and a
package the namespace check cannot cover), MathTex-only (equations and particle models, no
structural formulas), and bundled SVGs (a fixed human-drawn library, plus a file-read decision in
the render subprocess).

None is free, and the cheapest (MathTex-only) still buys a subject limited to the
equation-and-particle half of chemistry. Deferred until math + physics prove the pack seam. When
revisited, MathTex-only is the honest first increment; `chanim` is a product decision, not a pack.

## 10. Rough cost

| Stage | Estimate | Dominated by |
|---|---|---|
| 0 — the seam | ~1 day | Test updates, fallback restructure, hero serialization — not the registry itself |
| 1 — UI selection | 2–3 hours | Fieldset, endpoint + alias, client types |
| 2 — physics | 2–3 days | Writing `layouts.md` against real renders, and curating the catalogue |

The render-and-watch loop in stage 2 is the irreducible part. It is not compressible by writing a
longer prompt.
