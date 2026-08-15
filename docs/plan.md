# AI Micro-Lesson Studio — Hackathon Development Plan

## 1. Goal and MVP boundary

Build a German-language, teacher-only web app that lets a Gymnasium mathematics teacher select a grade, topic, subtopic, difficulty, learning objective, and teaching method; review an AI-generated storyboard; and produce:

- One German narrated Manim video, 1–2 minutes long, rendered at 720p/30fps.
- Burned-in German captions.
- Three matching Manim recap cards as PNG files.
- In-app preview and downloads for all artifacts.

The primary user is a time-poor Gymnasium mathematics teacher. Students aged approximately 10–16 consume the generated material but do not use the app directly.

The hackathon build is local and single-user. Next.js and FastAPI run as ordinary local processes, while Manim runs as a validated subprocess inside the API workflow. The deeply tested hero lesson is Grade 8 linear functions: understanding slope.

### MVP success criteria

- A teacher can configure a lesson without writing a prompt.
- The first storyboard appears within approximately 30 seconds.
- After approval, a warmed environment produces the media within three minutes.
- The teacher can revise one storyboard section without regenerating the rest.
- Failed live generation can fall back to a clearly labeled cached hero lesson.

## 2. Agreed product flow

1. The teacher opens `Neues Erklärvideo`.
2. The teacher selects:
   - Grade 5–10
   - Topic and subtopic from a curated catalog
   - Level: support, standard, or challenge
   - Optional learning objective
   - Method: automatic, visual linking, worked example, or error analysis
3. The app generates a German storyboard containing 4–6 sections.
4. The storyboard is labeled `KI-Entwurf – Freigabe durch Lehrkraft erforderlich`.
5. Every section displays its purpose, narration, visual plan, equations, and expected duration.
6. The teacher can add a comment to one section and regenerate only that section.
7. The teacher approves the complete storyboard.
8. The app shows the stages `Vertonung → Code → Rendering → Prüfung → Fertig`.
9. The result screen shows the video and three recap cards with download actions.

## 3. Technical shape

Use two ordinary local processes:

- `web`: Next.js, TypeScript, and Tailwind CSS, started with `npm run dev`.
- `api`: FastAPI orchestration, LangChain model calls, ElevenLabs integration, job state, AST validation, and Manim subprocess execution, started with Uvicorn.

Install Python, Manim Community, LaTeX, and FFmpeg directly on the controlled demo laptop during Sprint 0. Use a local `jobs/` folder for metadata, generated code, audio, captions, videos, and cards. Process one render job at a time and persist job state as JSON files. Do not add Docker, Redis, cloud storage, authentication, or a production database to the MVP.

Before starting Manim, validate generated code with the AST and Manim API allowlists. Launch the subprocess with a clean working directory, timeout, explicit command arguments, and an environment that excludes model and ElevenLabs credentials. An optional renderer-only container with networking disabled may be added after the hackathon, but it is not part of the implementation plan.

### Suggested repository layout

```text
apps/web/                 Next.js teacher interface
services/api/             FastAPI orchestration and AI integrations
services/api/app/rendering.py  AST-validated Manim subprocess workflow
content/math/catalog.json Curated grade/topic/subtopic metadata
prompts/                  Shared, math, pedagogy, and Manim prompt modules
scripts/                  Local prerequisite and start scripts
```

### Model and prompt strategy

- Initialize the model through LangChain `init_chat_model`.
- Read `MODEL_PROVIDER` and `MODEL_NAME` from environment configuration.
- Use OpenAI for the hackathon path; keep Claude as a configuration option, not a second implementation.
- Reuse one configured model with separate prompts for planning, pedagogical review, code generation, visual checking, and repair.
- Require Pydantic structured output for storyboards and review results.
- Generate free-form Python only after the teacher has approved the storyboard.
- Compose runtime prompts from small modules: shared education rules, mathematics rules, grade band, topic metadata, method, difficulty, Manim rules, and teacher comments.

### Manim code-generation contract

The code-generation prompt must enforce these rules. The model returns one complete Python file with no Markdown fences or explanation.

**Hard restrictions:**

- Use Manim Community syntax only. Reject ManimGL APIs such as `ShowCreation`, `GraphScene`, `TexMobject`, and `get_graph`; use `Create`, `Axes`, `MathTex`, and `plot`.
- Put German prose, including umlauts, only in `Text`. Keep `MathTex` limited to mathematical notation and never use LaTeX `\text{}` containing umlauts.
- Allow imports only from `manim`, `numpy`, and `math`.
- Forbid file, network, and subprocess access plus `open`, `eval`, and `exec`.
- Do not call `add_sound`; narration is muxed after rendering.
- Do not draw captions in Manim; captions are burned from SRT with FFmpeg.
- Do not overlap mobjects. Position related elements with `next_to` and an explicit `buff`.
- Keep content within `x ∈ [-6.5, 6.5]` and `y ∈ [-3.5, 3.5]`; scale wide content to fit.
- Use font sizes of at least 28.
- Pair every color distinction with a text or symbol label.
- Derive section timing from the supplied narration timestamps instead of hardcoding the total duration.

**Required structure:**

- Implement one method per storyboard section: `section_1(self, duration)`, `section_2(self, duration)`, and so on, called in order from `construct`.
- Track animation time within each method and call `self.wait(remaining)` when the section finishes before its target duration.
- Define and reuse top-level palette constants such as `VAR_COLOR`, `CHANGE_COLOR`, `RESULT_COLOR`, and `ERROR_COLOR`.
- Provide one standard axes factory with shared ranges, tick labels, and font sizes for the video and recap cards.
- Clear all current mobjects through a reusable transition helper between sections.
- Render key formulas with `MathTex(...).scale(1.2)` or larger.
- Use `ValueTracker` and `always_redraw` for the slope point and slope-triangle animation.
- Implement each recap card as a separate `Scene` class that reuses the palette and axes factory and can be rendered with `-s`.
- End `construct` with `self.wait(1)`.

### Core data contracts

`LessonRequest`

- `grade`: integer 5–10
- `topic_id`: catalog identifier
- `subtopic_id`: catalog identifier
- `level`: `support | standard | challenge`
- `objective`: optional string
- `method`: `auto | visual_linking | worked_example | error_analysis`

`StoryboardSection`

- Stable section ID
- Title and purpose
- Speech-friendly German narration
- Visual and animation plan
- On-screen text and LaTeX expressions
- Estimated duration
- Optional retrieval or self-explanation prompt

`Storyboard`

- Lesson title and objective
- Selected teaching method or methods
- 4–6 ordered sections
- Exactly three recap-card specifications
- `draft | approved` state

`RenderJob`

- Job ID
- Status: `planning | awaiting_approval | narrating | coding | rendering | checking | ready | failed | cached_fallback`
- Attempt count and safe error summary
- Video and card artifact paths
- Live or cached provenance

### API surface

- `GET /api/catalog`
- `POST /api/storyboards`
- `POST /api/storyboards/{id}/sections/{sectionId}/revise`
- `POST /api/storyboards/{id}/approve`
- `GET /api/jobs/{jobId}`
- `GET /api/jobs/{jobId}/artifacts/{artifactName}`

## 4. Sprint plan

### Sprint 0 — Foundation and contracts

**Time box:** 2–3 hours

**Goal:** Prepare the demo laptop and freeze the interfaces used by all team members.

**Build:**

- Scaffold the Next.js app and FastAPI service.
- Add `.env.example`, health endpoint, prerequisite checker, and separate local start scripts.
- Install Python, Manim Community, LaTeX, and FFmpeg on the demo laptop on day one.
- Create the local virtual environment and frontend dependency installation.
- Keep model and ElevenLabs secrets in the FastAPI environment and strip them from the Manim subprocess environment.
- Define the Pydantic request, storyboard, section, and render-job models.
- Add the API routes with placeholder responses so frontend work can proceed independently.
- Add a curated JSON catalog with two topic families per grade:
  - Grade 5: integers/number lines; geometric basics/angles
  - Grade 6: fractions/rational numbers; percentages/proportions
  - Grade 7: expressions/linear equations; data/geometric constructions
  - Grade 8: linear functions; systems of equations/probability
  - Grade 9: square roots/Pythagoras; quadratic functions/similarity
  - Grade 10: exponential growth/logarithms; trigonometry/solid geometry
- Mark the catalog as a typical progression, not binding nationwide curriculum alignment.

**Done when:** The prerequisite script passes, both local processes start, the UI loads the catalog from the API, and the API can render a fixed Manim smoke scene.

### Sprint 1 — Teacher input and storyboard approval

**Time box:** 4–5 hours

**Goal:** Complete the teacher workflow up to the approval boundary without depending on the media pipeline.

**Build:**

- Create a German single-page stepper with `Konfigurieren`, `Entwurf prüfen`, `Generieren`, and `Ergebnis` states.
- Implement cascading grade, topic, and subtopic selectors.
- Add level, optional objective, and method controls with sensible defaults.
- Add the runtime prompt composer and mathematics subject pack.
- Implement the three methods:
  - `Visuell verknüpfen`
  - `Gelöstes Beispiel`
  - `Fehler finden`
  - `Automatisch` may select or combine them.
- Make difficulty change scaffolding, number complexity, labels, and reasoning demand; do not implement student learning-style profiles.
- Generate a strict 4–6-section German storyboard.
- Run one lightweight model review for mathematical consistency, age suitability, and schema completeness before displaying it.
- Display the AI-draft label and section cards.
- Implement per-section comments and revision while preserving every untouched section ID and content.
- Require explicit teacher approval before starting narration or code generation.

**Done when:** The slope hero produces an editable German storyboard, one section can be revised independently, and approval creates a render job.

### Sprint 2 — Narration, Manim generation, and artifacts

**Time box:** 7–8 hours

**Goal:** Convert an approved storyboard into the final video and recap cards.

**Build:**

- Join approved narration into one German script while keeping spoken mathematics separate from displayed LaTeX.
- Call the ElevenLabs timestamp endpoint using one configured German voice.
- Convert timestamps into animation timing and caption data.
- Generate Manim Python containing:
  - One continuous `LessonVideo` class
  - Three static recap-card classes
- Add an AST allowlist before execution:
  - Permit Manim and required mathematics/numerical modules.
  - Reject filesystem, process, network, dynamic execution, and unrestricted imports.
  - Validate referenced Manim classes, methods, and attributes against the supported API allowlist so hallucinated or ManimGL-only names fail before rendering.
- Run only validated code from its job directory in a credential-scrubbed Manim subprocess.
- Run a cheap `-ql` render first and extract representative frames.
- Check the low-quality frames for clipping, overlaps, unreadable text, missing elements, and mismatch with the approved storyboard.
- Feed safe validation or render errors to the repair prompt, allowing no more than two combined repair attempts.
- After checks pass, render the video once with `-qm` at 720p/30fps and render the recap-card scenes with `-s`.
- Add the narration track and burn German captions with FFmpeg.
- Persist job progress and expose it through polling.
- Build the progress screen, video player, recap-card gallery, and download actions.

**Done when:** An approved slope storyboard passes AST and low-quality visual checks, then produces one playable narrated 720p MP4 with captions and three downloadable Manim PNG cards.

### Sprint 3 — Reliability, visual polish, and demo preparation

**Time box:** 3–4 hours

**Goal:** Make the main path understandable and reliable during judging.

**Build:**

- Create and bundle a cached, polished hero video and three hero cards.
- Use the cached artifacts only after a live failure and label them `Vorgefertigtes Demo-Beispiel`.
- Apply the modern classroom visual system:
  - 16:9 dark neutral canvas
  - High-contrast text
  - Large equations
  - Consistent concept, result, highlight, and error colors
  - Minimal on-screen text
  - Captions kept clear of important mathematics
  - No color-only meaning
- Finalize the slope hero sequence: real-world hook, rise/run animation, formula connection, worked example, student prompt, and recap.
- Warm the model and Manim render path before the demonstration.

**Done when:** The live hero path finishes within the target time or transitions clearly to the cached fallback, with no broken screen or ambiguous status.

## 5. Team split

For four people:

- Frontend: teacher form, storyboard cards, progress, preview, downloads.
- AI/API: schemas, prompt composition, storyboard/revision, job orchestration.
- Media: ElevenLabs timing, Manim generation contract, subprocess rendering, captions, cards.
- Content/demo: catalog, slope hero, visual consistency, fallback, final smoke run.

For two people, combine frontend with content/demo and combine AI/API with media.

## 6. Minimal verification

Only perform these required checks:

1. **Hero-path smoke check:** Grade 8 slope → storyboard → one section revision → approval → playable MP4 and three downloadable PNGs.
2. **Safety/failure check:** unsafe Python is rejected, rendering stops after two repair attempts, and no secret reaches the renderer output or visible logs.
3. **Fallback check:** simulate an external API or render failure and confirm the cached hero result is clearly labeled.

Do not spend hackathon time on coverage targets, load tests, broad cross-browser matrices, production security certification, or exhaustive testing of every catalog item.

## 7. Explicit non-goals

- Physics and chemistry generation in the MVP
- Slides or editable presentations
- Student accounts or student progress tracking
- Teacher authentication or project history
- LMS integration or public sharing links
- Arbitrary free-text topics
- Individual student profiling or learning-style claims
- State-specific curriculum compliance claims
- Analytics, billing, cloud deployment, or production scaling
- Multiple voice selection
- Docker or production-grade code isolation

Future subjects should be added through new subject packs, catalogs, teaching-method guidance, and validation rules without changing the approved-storyboard and artifact pipeline.
