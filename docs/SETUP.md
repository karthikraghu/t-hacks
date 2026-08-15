# Setup map

A one-page picture of what this system is, how to run it, and where to extend it.

## What it does

A teacher picks a grade, topic and subtopic, reviews an AI-generated storyboard, approves it, and receives
a narrated Manim video plus three recap card PNGs. Content is in English; the intended audience is
mathematics teachers at a German Gymnasium.

## The two processes

| Process | Location | Start with | Port |
| --- | --- | --- | --- |
| Web UI | `apps/web` (Next.js) | `./scripts/start-web.ps1` | 3000 |
| API | `services/api` (FastAPI) | `./scripts/start-api.ps1` | 8000 |

Manim runs as a subprocess of the API, not as a third service. There is no database, queue, or Docker:
job state is JSON files under `jobs/`.

## The happy path, end to end

```
Teacher fills the form
  └─ POST /api/storyboards ........ model writes a storyboard, a second model call reviews it
Teacher reads the sections, optionally comments on one
  └─ POST .../sections/{id}/revise . only that section is regenerated, other section IDs are preserved
Teacher approves
  └─ POST .../approve ............. creates a RenderJob and returns immediately
      background pipeline (services/api/app/pipeline.py):
        1. narrate ....... ElevenLabs with timestamps -> narration.mp3, captions.srt, section durations
        2. code .......... model writes one Manim file -> lesson.py
        3. check ......... up to 3 attempts, so 2 repairs:
                             a. AST validation ......... services/api/app/validation.py
                             b. fast -ql preview ....... one frame per section
                             c. sync gate .............. animation length vs narration length
                             d. frame bounds gate ...... content cut off at a frame edge
                             e. visual review .......... model looks at the frames
        4. final ......... -qm 720p render, three -s recap cards, FFmpeg mux + burned captions
Teacher polls GET /api/jobs/{id} and gets the player, cards and downloads
```

If any step fails and the request is the hero lesson, the job serves the prepared bundle in `fallback/`
and is labelled as a demo example instead of failing.

## Where things live

| Concern | File |
| --- | --- |
| Job orchestration and the repair loop | `services/api/app/pipeline.py` |
| Manim subprocess, gates, frame sampling | `services/api/app/rendering.py` |
| AST and API safety rules | `services/api/app/validation.py` |
| Deterministic layout gate | `services/api/app/frame_checks.py` |
| ElevenLabs timing and SRT | `services/api/app/narration.py` |
| Model calls | `services/api/app/ai.py` |
| Prompts, one per job | `prompts/*.md` |
| Curriculum catalog | `content/math/catalog.json` |
| Fixed hero lesson source | `fallback/hero_lesson.py` |
| Teacher UI, one page | `apps/web/app/page.tsx` |

## Run it

```powershell
# once
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r services\api\requirements.txt
npm install --prefix apps\web
./scripts/check-prereqs.ps1

# every time
./scripts/start-api.ps1   # terminal 1
./scripts/start-web.ps1   # terminal 2
```

`.env` needs `MODEL_NAME`, the matching provider key, `ELEVENLABS_API_KEY` and `ELEVENLABS_VOICE_ID`.

## Check it

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m unittest tests.test_minimal_checks -v   # free, seconds
.\.venv\Scripts\python.exe -m compileall -q services\api scripts      # free
npm run typecheck --prefix apps\web                                   # free
.\.venv\Scripts\python.exe scripts\run_live_smoke.py                  # paid, about 3 minutes
```

When a live run fails, read `jobs/jobs/<job-id>/attempts.log`. It records what each attempt was rejected
for, and `lesson_attempt_N.py` holds the code each repair produced.

## Lesson size is configurable, and small by default

A new lesson targets **2 sections and about 30 seconds**, set by `lesson_target_sections` and
`lesson_target_seconds` in `services/api/app/settings.py` and passed to the planner as `constraints`.

Small is the default on purpose. A 30 second lesson renders in a fraction of the time of a two minute one,
so the paid live path can be tested in a couple of minutes instead of five, and each section has room to
breathe rather than crowding the frame. Raise the two target values to produce longer lessons; the accepted
validation range (`lesson_min_*` / `lesson_max_*`, currently 2–6 sections and 25–120 seconds) is wider than
the target so the bundled five-section hero example still validates.

## Where to build further

- **A new subject or topic**: add entries to `content/math/catalog.json`. Nothing else needs to change for
  the storyboard path; only add a prompt module if the subject needs its own rules.
- **A new teaching method**: add it to `TeachingMethod` in `models.py`, describe it in
  `prompts/methods.md`, and add a label in `page.tsx`.
- **Stricter or looser visual gates**: the two deterministic gates are `_sync_issues` in `rendering.py`
  and `frame_checks.py`. Both feed the same repair loop, so a new gate is a function that returns a list
  of English issue strings.
- **A different voice**: `ELEVENLABS_VOICE_ID` in `.env`. The configured voice is a German one speaking
  English through the multilingual model; swap it for a native English voice if the accent matters.

## Deliberate non-goals

No Docker, auth, database, Redis, cloud storage, or physics and chemistry generation. Two repair attempts
maximum. See `docs/plan.md` for the agreed scope and `docs/HANDOFF.md` for current state and open items.
