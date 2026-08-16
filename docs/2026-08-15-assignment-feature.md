# Assignment Feature Implementation Plan

> Trimmed 2026-08-15. Every step below is on the critical path; what was removed and why is listed
> in [Removed from the original plan](#removed-from-the-original-plan) at the end.

**Goal:** A teacher publishes an assignment that splits the work into AI-assistable parts and a
cognitive core; when a student submits the core work, the AI asks exactly one question grounded in
the student's own text, and their answer is weighed into the mark.

**Architecture:** A second, fully synchronous entity family beside the existing storyboard flow,
reusing the same `Storage`/`AIService`/route machinery and touching none of `GenerationPipeline`,
`BackgroundTasks`, `LocalRenderer` or `ElevenLabsNarration`. Two guarantees are structural rather
than prompted: "exactly one question" is a single scalar `question: str` on the JSON-schema model,
and "grounded in the student's work" is a deterministic Python gate that verifies a quoted span
really occurs in the submission before anything is persisted.

**Tech Stack:** FastAPI, Pydantic v2, pydantic-settings, LangChain `init_chat_model`, Next.js
16.3.1, React 19.1.1, stdlib `unittest`.

**Seven tasks, in order.** Tasks 1–5 are the backend and can be done in one sitting; 6–7 are the
web client. Nothing is optional.

## Global Constraints

Every task's requirements implicitly include this section. All values are verified against the real
files.

**Python / API**

- `services/api/app/models.py` stays **one flat module**. No `models/` package. Header stays exactly
  `from __future__ import annotations` / `from enum import StrEnum` / `from typing import Literal` /
  `from pydantic import BaseModel, Field, field_validator`.
- **`Field(...)` with Ellipsis is never used.** Required fields are bare annotations or
  `Field(min_length=…)`.
- **No `Field` constraints on a stored model.** Stored models are re-parsed from disk with
  `model_validate_json`; a constraint added later turns every existing file into a 500 on GET. This
  is why `SubmissionProbe` and `SubmissionEvaluation` restate their fields bare instead of
  inheriting from the `Generated…` pair.
- **Never `default_factory=uuid4` on an id.** Ids are minted at the call site as `uuid4().hex`.
- `@field_validator` outermost, `@classmethod` immediately below it.
- On a `list[...]`, `min_length`/`max_length` mean **item count**; on a `str`, characters.
- `with_structured_output(Model, method="json_schema")` — `method` is never omitted and never
  another value. Structured models must be JSON-schema-safe: no `dict[str, Any]`, no unions beyond
  `X | None`.
- `init_chat_model` is called in exactly one place (`AIService.model`). Do not add `temperature`,
  `max_tokens`, `timeout`, or `max_retries` anywhere.
- Every `json.dumps` uses `ensure_ascii=False`. Free-text student input is a **named JSON key in the
  human message**, never concatenated into the system prompt.
- System prompts are `"\n\n".join([...])` of `.md` files, **always led by `shared_education.md`**. A
  new prompt file is inert until added to such a list — nothing globs `prompts/*.md`.
- Route handlers are **plain sync `def`**, never `async def` (they do blocking LLM and file I/O;
  FastAPI threadpools sync defs).
- Handlers reach `storage` / `ai` / `settings` as **module-level globals by bare name**. No
  `Depends()`, no closures.
- Guard order in every route: **exists → 404, state legal → 409, AI call in its own `try` → 422**.
  `from error` on every re-raise.
- Status codes in use: **404**, **409**, **422**. No 400, no 500, no custom handlers.
- **CORS allows only `["GET", "POST"]`** with only `Content-Type`. Every mutation is a POST to a
  verb-suffixed sub-path. A `PUT`/`PATCH`/`DELETE` route passes curl, then fails browser preflight
  as the misleading "The API did not answer".
- `Storage._write` never takes the lock; the public `save_*` does. `threading.Lock` is non-reentrant
  — a save calling a save deadlocks.
- New `Settings` fields are plain snake_case attributes with a literal default and a rationale
  comment. **Do not name anything `model_*`** — that collides with Pydantic's protected namespace.
  Use `assignment_probe_weight`.
- `settings` is one shared mutable `@lru_cache`d object. Treat it as read-only in handlers.

**Frontend**

- **Tailwind is installed and completely inert.** `tailwind.config.ts` is the bare stub and **zero
  utility classes appear in any `.tsx`**. All styling is ~95 hand-written semantic classes in
  `apps/web/app/globals.css` driven by `:root` custom properties. Never write a utility class; never
  write a raw hex colour.
- Colour semantics: `--pen` blue = primary/interactive, `--red` = **teacher's marks only**,
  `--marker` yellow = "you are here" / prepared example, `--paper` = page, `--card` = raised surface.
- `app/layout.tsx` is the only server component. Everything else is `"use client"`. All fetching is
  browser-side.
- **Never a bare `fetch` in a component** — one arrow function per endpoint on the `api` object in
  `lib/api.ts`.
- `lib/types.ts` is a **hand-maintained mirror** with snake_case field names preserved verbatim;
  every `StrEnum` becomes a string-literal union of identical values. There is no codegen.
  `npm run typecheck` is the only guard.
- `lib/labels.ts` is centralised **only for enum values**, typed `Record<Enum, string>`. All other
  copy is inline British English in the JSX — teacherly, full sentences, no exclamation marks, no
  emoji.
- Components: `"use client"` first line, local `interface Props`, **named** `export function`
  (default export only for `page.tsx`), props alphabetised in interface and destructure, no
  return-type annotation.
- Numbers that carry meaning get `.u-mono`.

**Testing**

`docs/HANDOFF.md` pins this: *"Keep tests minimal … Do not add broad tests."* This plan writes
**one** test: the pure grounding gate in Task 3, which is the only non-obvious logic in the feature.
Everything else is verified by the `python -c` snippet at the end of each task and by the browser
walkthrough in Task 7. stdlib `unittest` only. No pytest, no `conftest.py`, no `TestClient`.

---

### Task 0: Make the repo runnable

`.venv` and `apps/web/node_modules` are both absent. Nothing below can be verified until this is
done.

**Files:** none created — environment only.

> The repo path contains a space (`/Users/speak2gokul01/Projects backup/t-hacks`), so **every `cd`
> below is quoted**. Dropping the quotes is the first thing that will break.

- [ ] **Step 1: Create the Python environment without Manim**

`services/api/requirements.txt` pins `manim==0.19.0` and `imageio-ffmpeg`, which are a slow,
build-prone install. This feature needs neither: `import manim` appears only *inside* a function
body (`services/api/app/validation.py:68`), so the API imports and serves without it. Install the
rest:

```bash
cd "/Users/speak2gokul01/Projects backup/t-hacks"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install \
  "fastapi==0.116.1" "uvicorn[standard]==0.35.0" "pydantic==2.11.7" \
  "pydantic-settings==2.10.1" "httpx==0.28.1" "langchain==0.3.27" \
  "langchain-openai==0.3.30" "langchain-anthropic==0.3.18"
```

The consequence of skipping Manim is that `tests.test_minimal_checks` and the render pipeline will
not run. That is the correct trade for this feature; install the full
`-r services/api/requirements.txt` later if you need the video path back.

If the system Python is too new for these pinned wheels and pip starts compiling from source, stop
and install Python 3.12 instead (`brew install python@3.12`, then
`python3.12 -m venv .venv`) — the repo targets 3.12.

- [ ] **Step 2: Verify the app imports**

```bash
cd "/Users/speak2gokul01/Projects backup/t-hacks" && .venv/bin/python -c "
from services.api.app import main
print('routes:', len([r for r in main.app.routes if hasattr(r, 'methods')]))
"
```
Expected: a route count with no traceback. This is the baseline — if it fails now, fix it before
starting, so later failures are attributable to your own work.

- [ ] **Step 3: Install the web dependencies**

```bash
npm install --prefix "/Users/speak2gokul01/Projects backup/t-hacks/apps/web"
npm run typecheck --prefix "/Users/speak2gokul01/Projects backup/t-hacks/apps/web"
```
Expected: typecheck passes with no output.

---

### Task 1: Models and settings

**Files:**
- Modify: `services/api/app/models.py` (enums at the top with the others; models after
  `RendererResult`)
- Modify: `services/api/app/settings.py` (one new field, after `lesson_max_seconds`)

**Interfaces:**
- Consumes: nothing.
- Produces: `TaskMode`, `SubmissionState`, `AssignmentTask`, `Assignment`, `SubmissionRequest`,
  `GeneratedProbe`, `SubmissionProbe`, `ProbeAnswerRequest`, `GeneratedEvaluation`,
  `SubmissionEvaluation`, `Submission`; `Settings.assignment_probe_weight: float`.

- [ ] **Step 1: Add the two enums beside the existing ones**

In `services/api/app/models.py`, after `class StoryboardState(StrEnum)` and its members:

```python
class TaskMode(StrEnum):
    AI_ASSISTABLE = "ai_assistable"
    CORE = "core"


class SubmissionState(StrEnum):
    SUBMITTED = "submitted"
    PROBED = "probed"
    ANSWERED = "answered"
    EVALUATED = "evaluated"
```

`ANSWERED` is the checkpoint between the student's answer being saved and the mark arriving. It is
what lets a failed marking call be retried instead of stranding the submission.

- [ ] **Step 2: Add the models at the end of the file, after `RendererResult`**

```python
class AssignmentTask(BaseModel):
    description: str
    mode: TaskMode
    rationale: str


class Assignment(BaseModel):
    id: str
    title: str
    brief: str
    tasks: list[AssignmentTask]


class SubmissionRequest(BaseModel):
    # Deliberately loose. Pydantic body validation produces FastAPI's own 422 body,
    # which bypasses the handcrafted `detail` sentences the frontend renders, so the
    # meaningful minimum is checked in the route instead. This bound only stops an
    # absurd payload from reaching the model.
    core_response: str = Field(min_length=1, max_length=6000)

    @field_validator("core_response")
    @classmethod
    def trim_core_response(cls, value: str) -> str:
        return value.strip()


class GeneratedProbe(BaseModel):
    # One scalar question field, never a list. The provider physically cannot return
    # two questions against this schema, which is what makes "exactly one" structural
    # rather than a prompt instruction the model may drift from.
    question: str = Field(min_length=10, max_length=240)
    quoted_span: str = Field(min_length=4, max_length=200)


class SubmissionProbe(BaseModel):
    question: str
    quoted_span: str


class ProbeAnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)

    @field_validator("answer")
    @classmethod
    def trim_answer(cls, value: str) -> str:
        return value.strip()


class GeneratedEvaluation(BaseModel):
    core_score: int = Field(ge=0, le=100)
    probe_score: int = Field(ge=0, le=100)
    strengths: list[str] = Field(default_factory=list, max_length=4)
    gaps: list[str] = Field(default_factory=list, max_length=4)
    comment: str = Field(min_length=20, max_length=800)


class SubmissionEvaluation(BaseModel):
    core_score: int
    probe_score: int
    weighted_score: float
    # Stored beside the score so a mark stays auditable after the setting changes.
    probe_weight: float
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    comment: str


class Submission(BaseModel):
    id: str
    assignment_id: str
    state: SubmissionState
    core_response: str
    probe: SubmissionProbe | None = None
    probe_answer: str | None = None
    evaluation: SubmissionEvaluation | None = None
```

`AssignmentTask` has no id: nothing looks a task up, and nothing interpolates one into a path. It is
also stored, so it carries no `Field` constraints.

- [ ] **Step 3: Add the setting**

In `services/api/app/settings.py`, immediately after `lesson_max_seconds: int = 120`:

```python
    # How much of the mark comes from the spoken answer rather than the written work.
    # 0.4 is high on purpose: the answer is the only part of a submission that cannot
    # be delegated, so it has to be worth enough to matter.
    assignment_probe_weight: float = 0.4
```

- [ ] **Step 4: Verify the module imports and the models behave**

```bash
cd "/Users/speak2gokul01/Projects backup/t-hacks" && .venv/bin/python -c "
from services.api.app.models import Assignment, AssignmentTask, GeneratedProbe, TaskMode
from services.api.app.settings import get_settings
task = AssignmentTask(description='Choose the summary figure', mode=TaskMode.CORE, rationale='This is the judgement')
a = Assignment(id='a1', title='Rainfall', brief='x' * 30, tasks=[task])
print('assignment ok:', a.tasks[0].mode)
print('probe is one question:', list(GeneratedProbe.model_json_schema()['properties']))
print('probe weight:', get_settings().assignment_probe_weight)
"
```
Expected: `core`, `['question', 'quoted_span']`, and `0.4`. The middle line is the "exactly one
question" guarantee, asserted against the real JSON schema.

- [ ] **Step 5: Commit**

```bash
git add services/api/app/models.py services/api/app/settings.py
git commit -m "Add assignment and submission models plus the probe weight setting"
```

---

### Task 2: Storage

**Files:**
- Modify: `services/api/app/storage.py`

**Interfaces:**
- Consumes: `Assignment`, `Submission` from Task 1.
- Produces: `Storage.save_assignment`, `Storage.load_assignment`, `Storage.list_assignments`,
  `Storage.save_submission`, `Storage.load_submission`.

- [ ] **Step 1: Extend the import**

```python
from .models import Assignment, RenderJob, Storyboard, Submission
```

- [ ] **Step 2: Add the two directories in `__init__`**

After `self.jobs = root / "jobs"`:

```python
        self.assignments = root / "assignments"
        self.submissions = root / "submissions"
```

and after the existing `self.jobs.mkdir(parents=True, exist_ok=True)`:

```python
        self.assignments.mkdir(parents=True, exist_ok=True)
        self.submissions.mkdir(parents=True, exist_ok=True)
```

Flat `assignments/<id>.json`, not a directory per id — the directory-per-id layout exists only
because render jobs own media files.

- [ ] **Step 3: Add the concrete save/load pairs at the end of the class**

One hand-written pair per entity, matching `save_storyboard`/`load_storyboard`. There is no generic
helper in this codebase and you are not adding one.

```python
    def save_assignment(self, assignment: Assignment) -> None:
        with self._lock:
            self._write(self.assignments / f"{assignment.id}.json", assignment)

    def load_assignment(self, assignment_id: str) -> Assignment:
        path = self.assignments / f"{assignment_id}.json"
        if not path.exists():
            raise FileNotFoundError(assignment_id)
        return Assignment.model_validate_json(path.read_text(encoding="utf-8"))

    def list_assignments(self) -> list[Assignment]:
        # Unlocked, like every other read. Sorted by filename so the order a teacher
        # sees does not depend on the filesystem.
        return [
            Assignment.model_validate_json(path.read_text(encoding="utf-8"))
            for path in sorted(self.assignments.glob("*.json"))
        ]

    def save_submission(self, submission: Submission) -> None:
        with self._lock:
            self._write(self.submissions / f"{submission.id}.json", submission)

    def load_submission(self, submission_id: str) -> Submission:
        path = self.submissions / f"{submission_id}.json"
        if not path.exists():
            raise FileNotFoundError(submission_id)
        return Submission.model_validate_json(path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Verify a round-trip and the missing-file contract**

```bash
cd "/Users/speak2gokul01/Projects backup/t-hacks" && .venv/bin/python -c "
import tempfile
from pathlib import Path
from services.api.app.models import Assignment, AssignmentTask, Submission, SubmissionState, TaskMode
from services.api.app.storage import Storage
with tempfile.TemporaryDirectory() as tmp:
    s = Storage(Path(tmp))
    task = AssignmentTask(description='Choose the figure', mode=TaskMode.CORE, rationale='judgement')
    s.save_assignment(Assignment(id='a1', title='Rainfall', brief='x' * 30, tasks=[task]))
    s.save_submission(Submission(id='s1', assignment_id='a1', state=SubmissionState.SUBMITTED, core_response='y' * 50))
    print('assignment round-trip:', s.load_assignment('a1').tasks[0].mode)
    print('submission round-trip:', s.load_submission('s1').state)
    print('list:', [a.id for a in s.list_assignments()])
    try:
        s.load_assignment('missing')
    except FileNotFoundError as error:
        print('missing raises FileNotFoundError:', error)
"
```
Expected: `core`, `submitted`, `['a1']`, and `missing raises FileNotFoundError: missing`.

- [ ] **Step 5: Commit**

```bash
git add services/api/app/storage.py
git commit -m "Persist assignments and submissions alongside storyboards"
```

---

### Task 3: The deterministic grounding gate

**Files:**
- Create: `services/api/app/probe.py`
- Create: `tests/test_assignment_flow.py`

**Interfaces:**
- Consumes: nothing (pure Python).
- Produces: `GroundingResult` (dataclass: `grounded: bool`, `issues: list[str]`),
  `check_grounding(quoted_span: str, student_text: str) -> GroundingResult`, `MINIMUM_SPAN_WORDS`.

**Why this is the heart of the feature.** A question about the topic in general can be answered by
the same assistant that may have written the submission. Only a question about a decision visible in
*this student's text* requires them to have made it. Asking the model to be grounded is not enough —
so it must return the span it quoted, and plain Python verifies that span really occurs. This mirrors
`validate_manim_source` / `check_frame_bounds`: a free deterministic gate around the paid model gate.

- [ ] **Step 1: Write the failing test**

Create `tests/test_assignment_flow.py`:

```python
"""The one check this feature needs.

The grounding gate is the only non-obvious logic here, and its failure mode is silent:
a fluent, plausible question about work the student never did looks exactly like a good
one. Everything else in the feature fails loudly or is visible in the browser.
"""

from __future__ import annotations

import unittest

from services.api.app.probe import MINIMUM_SPAN_WORDS, check_grounding


class AssignmentGroundingChecks(unittest.TestCase):
    submission = (
        "Rainfall for the year is in the table. The mean is 74 mm and the median is 58 mm. "
        "I used the median as the summary figure because July had 268 mm."
    )

    def test_span_copied_from_the_submission_is_grounded(self) -> None:
        result = check_grounding("I used the median as the summary figure", self.submission)
        self.assertTrue(result.grounded)
        self.assertEqual([], result.issues)

    def test_span_the_student_never_wrote_is_rejected(self) -> None:
        # The failure the gate exists for. Nothing may be persisted on this path.
        result = check_grounding("I calculated the standard deviation", self.submission)
        self.assertFalse(result.grounded)
        self.assertTrue(any("does not appear" in issue for issue in result.issues))

    def test_whitespace_and_case_differences_still_count_as_grounded(self) -> None:
        # Models reflow whitespace and change capitalisation when quoting. Holding the
        # span to byte equality would reject honest quotes far more often than it would
        # catch invented ones.
        result = check_grounding("  i USED   the median\nas the summary figure ", self.submission)
        self.assertTrue(result.grounded)

    def test_a_span_too_short_to_mean_anything_is_rejected(self) -> None:
        # "the" occurs in every submission ever written. A span that short proves the
        # model quoted nothing in particular.
        result = check_grounding("the", self.submission)
        self.assertFalse(result.grounded)
        self.assertTrue(any(str(MINIMUM_SPAN_WORDS) in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd "/Users/speak2gokul01/Projects backup/t-hacks" && .venv/bin/python -m unittest tests.test_assignment_flow -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'services.api.app.probe'`.

- [ ] **Step 3: Write the gate**

Create `services/api/app/probe.py`:

```python
"""The grounding gate: proof that the question came from the student's own writing.

A follow-up question is only worth asking if it could not have been asked without
reading this particular submission. The model returns the span it quoted, and this
module checks that span really occurs in the student's text before the question is
shown to anyone. Free, deterministic, and run before the result is persisted — the
same shape as `validate_manim_source` and `check_frame_bounds`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Below this a span proves nothing: "the" appears in every submission ever written.
MINIMUM_SPAN_WORDS = 3


@dataclass
class GroundingResult:
    grounded: bool
    issues: list[str] = field(default_factory=list)


def _normalise(text: str) -> str:
    """Lower-case, collapse whitespace, and straighten the quotes models introduce.

    Deliberately forgiving about presentation and strict about words. A model asked
    to copy a span reflows whitespace and changes capitalisation constantly; holding
    it to byte equality would reject honest quotes far more often than it would catch
    invented ones, and a false alarm on every question teaches everyone to ignore it.
    """
    straightened = text.replace("‘", "'").replace("’", "'")
    straightened = straightened.replace("“", '"').replace("”", '"')
    return " ".join(straightened.lower().split())


def check_grounding(quoted_span: str, student_text: str) -> GroundingResult:
    """Return the issues that stop this question being asked. Empty means grounded."""
    issues: list[str] = []
    span = _normalise(quoted_span)
    haystack = _normalise(student_text)
    words = len(span.split())

    if words < MINIMUM_SPAN_WORDS:
        issues.append(
            f"The quoted span is only {words} word(s); at least {MINIMUM_SPAN_WORDS} are "
            "needed to show the question follows the student's own writing."
        )
    elif span not in haystack:
        issues.append(
            "The quoted span does not appear in the submission, so the question was not "
            "drawn from the student's own work."
        )

    return GroundingResult(grounded=not issues, issues=issues)
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
cd "/Users/speak2gokul01/Projects backup/t-hacks" && .venv/bin/python -m unittest tests.test_assignment_flow -v
```
Expected: PASS, 4 tests.

- [ ] **Step 5: Commit**

```bash
git add services/api/app/probe.py tests/test_assignment_flow.py
git commit -m "Add the deterministic grounding gate for follow-up questions"
```

---

### Task 4: Prompts and the two AI methods

**Files:**
- Create: `prompts/probe.md`
- Create: `prompts/evaluation.md`
- Modify: `services/api/app/ai.py`

**Interfaces:**
- Consumes: `Assignment`, `Submission`, `GeneratedProbe`, `GeneratedEvaluation`, `TaskMode`.
- Produces: `AIService.probe_question(assignment, submission) -> GeneratedProbe`,
  `AIService.evaluate_submission(assignment, submission) -> GeneratedEvaluation`.

- [ ] **Step 1: Write the probe prompt**

Create `prompts/probe.md`. House shape: `#`-level headings, hyphen bullets, hard-wrapped around 100
columns, British English, calm and positively framed. It opens at `# Task` and does not re-declare
identity, because `shared_education.md` already supplies that.

```markdown
# Task

Ask the student one question about the thinking behind their submission.

The payload gives you `assignment_title`, `assignment_brief`, `core_tasks` — the parts the student
had to do themselves — and `student_response`, their own words. The parts the assignment allowed
them to delegate are deliberately not shown to you; there is nothing to learn from asking about
work that was permitted to be handed over.

# Constraints

- Ask exactly one question. Not two, and not one question with a second clause attached.
- The question must be about a choice, a number, or a claim that appears in `student_response`.
- Ask why they made that choice, or what would change if it were different. The reasoning behind a
  decision is not written down, which is what makes the question worth asking.
- A question that could be answered by someone who had not read `student_response` is the one thing
  to avoid. General knowledge of the topic must not be enough.
- Keep it under forty words and use plain language the student will recognise.
- If the submission is too thin to contain a decision, ask which part they found hardest and why.

# Output format

Return the question and the span of `student_response` it refers to.

- `question` — the single question, ending in a question mark.
- `quoted_span` — a short run of words copied from `student_response` exactly as the student wrote
  them. This is checked against their text automatically, so copy rather than paraphrase, and quote
  at least three words.
```

- [ ] **Step 2: Write the evaluation prompt**

Create `prompts/evaluation.md`:

```markdown
# Task

Mark a submission using both the work the student wrote and the answer they gave to one follow-up
question about it.

The payload gives you `assignment_title`, `assignment_brief`, `core_tasks`, `student_response`,
`question`, and `student_answer`.

# Constraints

- `core_tasks` are what the assignment is actually about, and they are the only work the student
  hands in. Judge those.
- Score the written work and the spoken answer separately. A submission can be well written and an
  answer can still fail to account for it; that gap is worth recording rather than averaging away.
- A short answer that names the real reason is a good answer. Judge whether the thinking is there,
  not how much was typed.
- Address the student directly and say what to do next, in concrete terms about this piece of work.
- Do not speculate about how the work was produced, and do not mention AI in the comment.

# Output format

- `core_score` — 0 to 100, how well `student_response` does the `core_tasks`.
- `probe_score` — 0 to 100, how far `student_answer` shows the student did that thinking themselves.
- `strengths` — up to four short sentences about what worked.
- `gaps` — up to four short sentences about what to change.
- `comment` — two or three sentences addressed to the student.
```

- [ ] **Step 3: Extend the models import in `ai.py`**

Add the new names to the existing `from .models import (...)` block, keeping it alphabetised:

```python
from .models import (
    Assignment,
    GeneratedEvaluation,
    GeneratedProbe,
    GeneratedSection,
    GeneratedStoryboard,
    LessonRequest,
    Storyboard,
    StoryboardReview,
    Submission,
    TaskMode,
    VisualReview,
)
```

- [ ] **Step 4: Add the two methods to `AIService`**

Append inside the class, after the existing methods. Both follow the canonical shape exactly: guard
clause, plain-dict payload, `with_structured_output(..., method="json_schema")` bound to a
role-named local, a two-element message list, and `ensure_ascii=False`.

```python
    def probe_question(self, assignment: Assignment, submission: Submission) -> GeneratedProbe:
        if not self.settings.model_is_configured:
            raise ModelNotConfigured("Asking the follow-up question requires a configured model.")
        context = {
            "assignment_title": assignment.title,
            "assignment_brief": assignment.brief,
            # Only the core tasks. Probing work the assignment allowed to be delegated
            # would tell nobody anything.
            "core_tasks": [
                task.description for task in assignment.tasks if task.mode == TaskMode.CORE
            ],
            # The student's text is a named key in the human turn, never part of the
            # system prompt: it is data, and the rules stay out of its reach.
            "student_response": submission.core_response,
        }
        examiner = self.model.with_structured_output(GeneratedProbe, method="json_schema")
        return examiner.invoke(
            [
                SystemMessage(
                    content="\n\n".join(
                        [self.prompt("shared_education.md"), self.prompt("probe.md")]
                    )
                ),
                HumanMessage(content=json.dumps(context, ensure_ascii=False)),
            ]
        )

    def evaluate_submission(
        self, assignment: Assignment, submission: Submission
    ) -> GeneratedEvaluation:
        if not self.settings.model_is_configured:
            raise ModelNotConfigured("Marking a submission requires a configured model.")
        context = {
            "assignment_title": assignment.title,
            "assignment_brief": assignment.brief,
            "core_tasks": [
                task.description for task in assignment.tasks if task.mode == TaskMode.CORE
            ],
            "student_response": submission.core_response,
            "question": submission.probe.question if submission.probe else "",
            "student_answer": submission.probe_answer or "",
        }
        marker = self.model.with_structured_output(GeneratedEvaluation, method="json_schema")
        return marker.invoke(
            [
                SystemMessage(
                    content="\n\n".join(
                        [self.prompt("shared_education.md"), self.prompt("evaluation.md")]
                    )
                ),
                HumanMessage(content=json.dumps(context, ensure_ascii=False)),
            ]
        )
```

- [ ] **Step 5: Verify the module compiles and both prompts load**

```bash
cd "/Users/speak2gokul01/Projects backup/t-hacks" && .venv/bin/python -m compileall -q services/api && .venv/bin/python -c "
from services.api.app.ai import AIService
from services.api.app.settings import get_settings
ai = AIService(get_settings())
for name in ('shared_education.md', 'probe.md', 'evaluation.md'):
    print(name, len(ai.prompt(name)), 'chars')
print('probe_question present:', hasattr(ai, 'probe_question'))
"
```
Expected: three non-zero character counts and `True`. A zero would mean the prompt file is empty or
`prompt_root` is misresolved.

- [ ] **Step 6: Commit**

```bash
git add prompts/probe.md prompts/evaluation.md services/api/app/ai.py
git commit -m "Add the probe and evaluation prompts and their model calls"
```

---

### Task 5: Seed assignment and routes

**Files:**
- Create: `services/api/app/seed_assignment.py`
- Modify: `services/api/app/main.py`

**Interfaces:**
- Consumes: everything from Tasks 1–4.
- Produces: `SEED_ASSIGNMENT_ID`, `seed_assignment()`; routes `GET /api/assignments`,
  `POST /api/assignments/{assignment_id}/submissions`, `POST /api/submissions/{submission_id}/probe`,
  `POST /api/submissions/{submission_id}/answer`.

Four routes, all GET or POST. CORS permits nothing else.

- [ ] **Step 1: Write the seed**

Create `services/api/app/seed_assignment.py`. Follows `hero.py`: a hand-built object with a fixed id,
so the whole feature is demoable with no API key configured.

```python
"""A worked example assignment, so the feature is demoable with no model configured.

The same reason `hero.py` exists. The split here is deliberately unarguable:
computing an average is arithmetic a machine should do, and deciding *which*
average represents the data fairly is the judgement the assignment is about.
"""

from __future__ import annotations

from .models import Assignment, AssignmentTask, TaskMode

#: Fixed, and shaped like `uuid4().hex` so it is safe to interpolate into a path.
SEED_ASSIGNMENT_ID = "5eed0000000000000000000000000001"


def seed_assignment() -> Assignment:
    return Assignment(
        id=SEED_ASSIGNMENT_ID,
        title="Rainfall report",
        brief=(
            "You are given the monthly rainfall for one year in millimetres. Produce a "
            "one-page report: a tidy table, one summary figure for the whole year, and a "
            "short paragraph saying what kind of year it was."
        ),
        tasks=[
            AssignmentTask(
                description="Lay the figures out as a table",
                mode=TaskMode.AI_ASSISTABLE,
                rationale="Formatting is presentation, not mathematics.",
            ),
            AssignmentTask(
                description="Work out the mean, the median and the range",
                mode=TaskMode.AI_ASSISTABLE,
                rationale="The arithmetic is mechanical once the method is chosen.",
            ),
            AssignmentTask(
                description="Draw the bar chart",
                mode=TaskMode.AI_ASSISTABLE,
                rationale="Plotting given numbers adds nothing to the reasoning.",
            ),
            AssignmentTask(
                description=(
                    "Choose which summary figure represents this year fairly, and say why"
                ),
                mode=TaskMode.CORE,
                rationale=(
                    "Deciding between the mean and the median for this data is the "
                    "judgement the assignment is about."
                ),
            ),
            AssignmentTask(
                description="Explain what the one unusual month means for your answer",
                mode=TaskMode.CORE,
                rationale="Reading an outlier is interpretation, not calculation.",
            ),
        ],
    )
```

- [ ] **Step 2: Wire the seed into `main.py`**

Add the new model names into the existing `from .models import (...)` block rather than a second
import statement, then two new imports:

```python
from .models import (
    JobStatus,
    LessonRequest,
    ProbeAnswerRequest,
    RenderJob,
    SectionRevisionRequest,
    Storyboard,
    StoryboardSection,
    StoryboardState,
    Submission,
    SubmissionEvaluation,
    SubmissionProbe,
    SubmissionRequest,
    SubmissionState,
)
from .probe import check_grounding
from .seed_assignment import SEED_ASSIGNMENT_ID, seed_assignment
```

After `pipeline = GenerationPipeline(...)`:

```python
# The worked example is written once at import, so the assignment list is never empty
# on a fresh machine and the feature demonstrates with no API key configured. Import
# already touches the filesystem here (Catalog parses its JSON, Storage mkdirs), so a
# write is consistent — but it must never raise, or the app becomes unimportable.
try:
    storage.load_assignment(SEED_ASSIGNMENT_ID)
except FileNotFoundError:
    storage.save_assignment(seed_assignment())
```

- [ ] **Step 3: Add the list route**

Append to `main.py`:

```python
@app.get("/api/assignments")
def list_assignments() -> dict[str, object]:
    return {"assignments": [assignment.model_dump() for assignment in storage.list_assignments()]}
```

- [ ] **Step 4: Add the submit route**

```python
@app.post("/api/assignments/{assignment_id}/submissions", response_model=Submission)
def create_submission(assignment_id: str, request: SubmissionRequest) -> Submission:
    try:
        storage.load_assignment(assignment_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Assignment not found.") from error

    # Checked here rather than as a Field constraint: pydantic body validation returns
    # FastAPI's own 422 shape, which the frontend renders as an object-ish string
    # instead of this sentence.
    if len(request.core_response) < 40:
        raise HTTPException(
            status_code=422,
            detail="Write a little more before submitting, so the work can be marked fairly.",
        )

    submission = Submission(
        id=uuid4().hex,
        assignment_id=assignment_id,
        state=SubmissionState.SUBMITTED,
        core_response=request.core_response,
    )
    storage.save_submission(submission)
    return submission
```

- [ ] **Step 5: Add the probe route — where "exactly one question" is enforced**

```python
@app.post("/api/submissions/{submission_id}/probe", response_model=Submission)
def probe_submission(submission_id: str) -> Submission:
    try:
        submission = storage.load_submission(submission_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Submission not found.") from error
    # One question per submission, structurally: a second call cannot reach the model.
    if submission.state != SubmissionState.SUBMITTED:
        raise HTTPException(
            status_code=409, detail="This submission already has its question."
        )
    try:
        assignment = storage.load_assignment(submission.assignment_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Assignment not found.") from error

    try:
        generated = ai.probe_question(assignment, submission)
    except (ModelNotConfigured, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    # The free deterministic gate, run before anything is persisted: a question the
    # student's own words do not support is not asked at all.
    grounding = check_grounding(generated.quoted_span, submission.core_response)
    if not grounding.grounded:
        raise HTTPException(status_code=422, detail="; ".join(grounding.issues))

    submission.probe = SubmissionProbe(
        question=generated.question,
        quoted_span=generated.quoted_span,
    )
    submission.state = SubmissionState.PROBED
    storage.save_submission(submission)
    return submission
```

- [ ] **Step 6: Add the answer route — where the answer enters the mark**

```python
@app.post("/api/submissions/{submission_id}/answer", response_model=Submission)
def answer_probe(submission_id: str, request: ProbeAnswerRequest) -> Submission:
    try:
        submission = storage.load_submission(submission_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Submission not found.") from error
    # ANSWERED is legal here as well as PROBED: the answer is saved before the model is
    # asked, so a marking failure leaves the submission in ANSWERED. Accepting only
    # PROBED would 409 every retry and strand the student with no mark.
    if submission.state not in (SubmissionState.PROBED, SubmissionState.ANSWERED):
        raise HTTPException(
            status_code=409,
            detail="This submission is not waiting for an answer to its question.",
        )
    try:
        assignment = storage.load_assignment(submission.assignment_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Assignment not found.") from error

    # Recorded before the model is asked, so a marking failure never costs the student
    # their words.
    submission.probe_answer = request.answer
    submission.state = SubmissionState.ANSWERED
    storage.save_submission(submission)

    try:
        generated = ai.evaluate_submission(assignment, submission)
    except (ModelNotConfigured, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    # The weighting is arithmetic here, not a number the model chose: how much the
    # answer counts is a teaching decision and belongs in settings.
    weight = settings.assignment_probe_weight
    submission.evaluation = SubmissionEvaluation(
        core_score=generated.core_score,
        probe_score=generated.probe_score,
        weighted_score=round(
            generated.core_score * (1 - weight) + generated.probe_score * weight, 1
        ),
        probe_weight=weight,
        strengths=generated.strengths,
        gaps=generated.gaps,
        comment=generated.comment,
    )
    submission.state = SubmissionState.EVALUATED
    storage.save_submission(submission)
    return submission
```

- [ ] **Step 7: Verify the app imports and every route is registered**

```bash
cd "/Users/speak2gokul01/Projects backup/t-hacks" && .venv/bin/python -c "
from services.api.app import main
for route in main.app.routes:
    if hasattr(route, 'methods') and ('assignment' in route.path or 'submission' in route.path):
        print(sorted(route.methods), route.path)
print('seed present:', main.storage.load_assignment(main.SEED_ASSIGNMENT_ID).title)
"
```
Expected: exactly four assignment/submission routes, all `['GET']` or `['POST']` — **no
PUT/PATCH/DELETE**, which CORS would block in the browser — and `seed present: Rainfall report`.

- [ ] **Step 8: Commit**

```bash
git add services/api/app/seed_assignment.py services/api/app/main.py
git commit -m "Add the assignment routes, the one-question guard and the seeded example"
```

---

### Task 6: Frontend types, API client and labels

**Files:**
- Modify: `apps/web/lib/types.ts`
- Modify: `apps/web/lib/api.ts`
- Modify: `apps/web/lib/labels.ts`

**Interfaces:**
- Consumes: the four routes from Task 5.
- Produces: TS types `TaskMode`, `SubmissionState`, `AssignmentTask`, `Assignment`,
  `SubmissionProbe`, `SubmissionEvaluation`, `Submission`; `api.assignments`, `api.submit`,
  `api.probe`, `api.answerProbe`; `taskModeLabels`, `taskModes`.

- [ ] **Step 1: Mirror the models in `types.ts`**

Field names stay snake_case, matching the JSON on the wire exactly. Append:

```ts
export type TaskMode = "ai_assistable" | "core";
export type SubmissionState = "submitted" | "probed" | "answered" | "evaluated";

export interface AssignmentTask {
  description: string;
  mode: TaskMode;
  rationale: string;
}

export interface Assignment {
  id: string;
  title: string;
  brief: string;
  tasks: AssignmentTask[];
}

export interface SubmissionProbe {
  question: string;
  quoted_span: string;
}

export interface SubmissionEvaluation {
  core_score: number;
  probe_score: number;
  weighted_score: number;
  probe_weight: number;
  strengths: string[];
  gaps: string[];
  comment: string;
}

export interface Submission {
  id: string;
  assignment_id: string;
  state: SubmissionState;
  core_response: string;
  probe?: SubmissionProbe | null;
  probe_answer?: string | null;
  evaluation?: SubmissionEvaluation | null;
}
```

- [ ] **Step 2: Add the endpoints to `api.ts`**

Extend the type import and add four arrow functions to the `api` object. `request<T>` already handles
the base URL, the JSON headers, and pulling `detail` out of an error body — never call `fetch`
directly.

```ts
import type { Assignment, Catalog, LessonRequest, RenderJob, Storyboard, Submission } from "./types";
```

```ts
  assignments: () => request<{ assignments: Assignment[] }>("/api/assignments"),
  submit: (assignmentId: string, coreResponse: string) =>
    request<Submission>(`/api/assignments/${assignmentId}/submissions`, {
      method: "POST",
      body: JSON.stringify({ core_response: coreResponse }),
    }),
  probe: (submissionId: string) =>
    request<Submission>(`/api/submissions/${submissionId}/probe`, { method: "POST" }),
  answerProbe: (submissionId: string, answer: string) =>
    request<Submission>(`/api/submissions/${submissionId}/answer`, {
      method: "POST",
      body: JSON.stringify({ answer }),
    }),
```

- [ ] **Step 3: Add the enum labels**

In `apps/web/lib/labels.ts`, extend the type import and append. `Record<Enum, string>` is what makes
TS fail the build if a member is ever added without a label.

```ts
import type { JobStatus, Level, Method, TaskMode } from "./types";
```

```ts
export const taskModeLabels: Record<TaskMode, string> = {
  ai_assistable: "AI may help",
  core: "Your own thinking",
};

/** Core first: the point of the page is what the student has to do themselves. */
export const taskModes: TaskMode[] = ["core", "ai_assistable"];
```

- [ ] **Step 4: Typecheck**

```bash
npm run typecheck --prefix "/Users/speak2gokul01/Projects backup/t-hacks/apps/web"
```
Expected: passes silently. This is the only guard against the hand-maintained mirror drifting from
the Pydantic models.

- [ ] **Step 5: Commit**

```bash
git add apps/web/lib/types.ts apps/web/lib/api.ts apps/web/lib/labels.ts
git commit -m "Mirror the assignment models and endpoints in the web client"
```

---

### Task 7: The assignment UI

**Files:**
- Create: `apps/web/app/assignments/page.tsx`
- Create: `apps/web/components/AssignmentBrief.tsx`
- Create: `apps/web/components/SubmitStep.tsx`
- Create: `apps/web/components/ProbeStep.tsx`
- Create: `apps/web/components/EvaluationStep.tsx`
- Modify: `apps/web/app/globals.css`
- Modify: `apps/web/app/page.tsx` (one link in the header)

**Interfaces:**
- Consumes: Task 6's `api`, types and labels.
- Produces: the route `/assignments`.

A separate App Router route, not a fifth step in `app/page.tsx` — that machine's `STEPS` in
`StepRail.tsx` and `stepOrder` in `page.tsx` are two parallel lists coupled only by array position,
and a mismatch fails silently.

- [ ] **Step 1: Add the five new CSS classes**

Everything else reuses the existing vocabulary. Append to `apps/web/app/globals.css`, built from the
`:root` tokens — never a raw hex, never a Tailwind utility.

```css
/* Assignment: the split between delegable work and the student's own thinking. */
.task-split {
  display: grid;
  gap: 10px;
}

.task-row {
  border: 1px solid var(--rule-soft);
  border-radius: var(--radius-s);
  padding: 10px 12px;
}

.task-row.is-core {
  background: var(--pen-wash);
  border-color: var(--rule);
}

/* The one question. Marker yellow says "you are here" and nothing else does. */
.probe-card {
  background: var(--card);
  border: 1px solid var(--rule);
  border-left: 4px solid var(--marker);
  border-radius: var(--radius);
  padding: 16px 18px;
}

.probe-quote {
  border-left: 2px solid var(--rule);
  color: var(--ink-2);
  font-style: italic;
  margin: 10px 0 0;
  padding-left: 12px;
}

.score-row {
  display: flex;
  gap: 28px;
  margin: 4px 0 12px;
}
```

- [ ] **Step 2: Write the brief component**

Create `apps/web/components/AssignmentBrief.tsx`. The group heading already names the mode, so the
rows carry no tag — the blue wash on `.is-core` is the distinction.

```tsx
"use client";

import { taskModeLabels, taskModes } from "@/lib/labels";
import type { Assignment } from "@/lib/types";

interface Props {
  assignment: Assignment;
}

export function AssignmentBrief({ assignment }: Props) {
  return (
    <section className="card">
      {/* `.card` carries no padding of its own — every direct child is a `.section`,
          exactly as in SetupStep. */}
      <div className="section">
        <h2 className="u-h2">{assignment.title}</h2>
        <p className="u-muted u-spaced">{assignment.brief}</p>
      </div>

      {taskModes.map((mode) => (
        <div className="section" key={mode}>
          <p className="u-label">{taskModeLabels[mode]}</p>
          <div className="task-split">
            {assignment.tasks
              .filter((task) => task.mode === mode)
              .map((task) => (
                <div
                  className={mode === "core" ? "task-row is-core" : "task-row"}
                  key={task.description}
                >
                  {task.description}
                  <span className="u-note"> {task.rationale}</span>
                </div>
              ))}
          </div>
        </div>
      ))}
    </section>
  );
}
```

- [ ] **Step 3: Write the submit step**

Create `apps/web/components/SubmitStep.tsx`:

```tsx
"use client";

import { FormEvent } from "react";

interface Props {
  busy: boolean;
  draft: string;
  onDraft: (value: string) => void;
  onExample: () => void;
  onSubmit: () => void;
}

export function SubmitStep({ busy, draft, onDraft, onExample, onSubmit }: Props) {
  function send(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <form onSubmit={send}>
      <div className="page-head">
        <p className="u-label">Your work</p>
        <h1 className="u-display">Hand in the part that is yours</h1>
      </div>

      <div className="card">
        <div className="field">
          <label htmlFor="core">Your reasoning</label>
          <textarea
            id="core"
            onChange={(event) => onDraft(event.target.value)}
            placeholder="Explain the choice you made and why you made it."
            rows={10}
            value={draft}
          />
        </div>
        <button className="btn btn-quiet btn-small" onClick={onExample} type="button">
          Use the worked example
        </button>
      </div>

      <div className="approve-bar">
        <p className="u-muted">
          After you hand in, you will be asked one question about your own reasoning. It counts
          towards the mark.
        </p>
        <div className="approve-actions">
          <button className="btn btn-primary" disabled={busy} type="submit">
            {busy ? "Reading your work…" : "Hand in"}
          </button>
        </div>
      </div>
    </form>
  );
}
```

- [ ] **Step 4: Write the probe step**

Create `apps/web/components/ProbeStep.tsx`:

```tsx
"use client";

import { KeyboardEvent, useState } from "react";
import type { SubmissionProbe } from "@/lib/types";

interface Props {
  busy: boolean;
  onAnswer: (answer: string) => void;
  probe: SubmissionProbe;
}

export function ProbeStep({ busy, onAnswer, probe }: Props) {
  const [draft, setDraft] = useState("");

  function send() {
    const answer = draft.trim();
    if (answer) onAnswer(answer);
  }

  function keys(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      send();
    }
  }

  return (
    <>
      <div className="page-head">
        <p className="u-label">One question</p>
        <h1 className="u-display">About your own reasoning</h1>
      </div>

      <div className="probe-card">
        <p>{probe.question}</p>
        <p className="probe-quote">“{probe.quoted_span}”</p>
      </div>

      <div className="alert alert-info" role="note">
        <p>
          Answer in your own words. There is no right length — say what you were thinking when you
          made that choice.
        </p>
      </div>

      <div className="mark-form">
        <div className="field">
          <label htmlFor="answer">Your answer</label>
          <textarea
            id="answer"
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={keys}
            rows={5}
            value={draft}
          />
        </div>
        <div className="mark-actions">
          <button className="btn btn-primary" disabled={busy} onClick={send} type="button">
            {busy ? "Marking…" : "Send answer"}
          </button>
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 5: Write the evaluation step**

Create `apps/web/components/EvaluationStep.tsx`:

```tsx
"use client";

import type { SubmissionEvaluation } from "@/lib/types";

interface Props {
  evaluation: SubmissionEvaluation;
}

export function EvaluationStep({ evaluation }: Props) {
  return (
    <>
      <div className="page-head">
        <p className="u-label">Marked</p>
        <h1 className="u-display">{evaluation.weighted_score}</h1>
      </div>

      <div className="card">
        <div className="section">
          {/* Both parts shown, never just the total: the point of the feature is that
              the written work and the spoken answer are two different measurements. */}
          <div className="score-row">
            <p>
              <span className="u-label">Written work</span>{" "}
              <span className="u-mono">{evaluation.core_score}</span>
            </p>
            <p>
              <span className="u-label">Your answer</span>{" "}
              <span className="u-mono">{evaluation.probe_score}</span>
            </p>
            <p>
              <span className="u-label">Answer counts for</span>{" "}
              <span className="u-mono">{Math.round(evaluation.probe_weight * 100)}%</span>
            </p>
          </div>

          <p>{evaluation.comment}</p>
        </div>

        <div className="section">
          <p className="u-label">What worked</p>
          <ul>
            {evaluation.strengths.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="section">
          <p className="u-label">What to change</p>
          <ul>
            {evaluation.gaps.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 6: Write the page**

Create `apps/web/app/assignments/page.tsx`. Default export only here; it owns all state, all API
calls and the single error banner.

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { AssignmentBrief } from "@/components/AssignmentBrief";
import { EvaluationStep } from "@/components/EvaluationStep";
import { ProbeStep } from "@/components/ProbeStep";
import { SubmitStep } from "@/components/SubmitStep";
import { api } from "@/lib/api";
import type { Assignment, Submission } from "@/lib/types";

type Step = "write" | "answer" | "marked";

const EXAMPLE =
  "Rainfall for the year is in the table. The mean is 74 mm and the median is 58 mm. " +
  "I used the median as the summary figure for the year. July had 268 mm, which is much " +
  "higher than every other month. Overall the year was fairly dry apart from one wet month.";

export default function AssignmentsPage() {
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [draft, setDraft] = useState("");
  const [step, setStep] = useState<Step>("write");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The text the current submission was created from. Handing in twice after a failed
  // probe reuses that submission instead of orphaning it; editing the work first has
  // to create a new one, because a stored core_response cannot be changed.
  const submittedDraft = useRef<string | null>(null);

  useEffect(() => {
    api
      .assignments()
      .then((body) => setAssignment(body.assignments[0] ?? null))
      .catch((reason) =>
        setError(reason instanceof Error ? reason.message : "The assignments could not be loaded."),
      );
  }, []);

  async function handIn() {
    if (!assignment) return;
    setBusy(true);
    setError(null);
    try {
      const text = draft.trim();
      let current = submission;
      if (!current || submittedDraft.current !== text) {
        current = await api.submit(assignment.id, text);
        submittedDraft.current = text;
        setSubmission(current);
      }
      const probed = await api.probe(current.id);
      setSubmission(probed);
      setStep("answer");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The work could not be handed in.");
    } finally {
      setBusy(false);
    }
  }

  async function answer(text: string) {
    if (!submission) return;
    setBusy(true);
    setError(null);
    try {
      const marked = await api.answerProbe(submission.id, text);
      setSubmission(marked);
      setStep("marked");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The answer could not be marked.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="main">
      <div className="shell stack">
        {error && (
          <div className="alert alert-error" role="alert">
            <p>{error}</p>
            <button className="btn btn-plain btn-small" onClick={() => setError(null)} type="button">
              Dismiss
            </button>
          </div>
        )}

        {assignment && <AssignmentBrief assignment={assignment} />}

        {step === "write" && (
          <SubmitStep
            busy={busy}
            draft={draft}
            onDraft={setDraft}
            onExample={() => setDraft(EXAMPLE)}
            onSubmit={handIn}
          />
        )}

        {step === "answer" && submission?.probe && (
          <ProbeStep busy={busy} onAnswer={answer} probe={submission.probe} />
        )}

        {step === "marked" && submission?.evaluation && (
          <EvaluationStep evaluation={submission.evaluation} />
        )}
      </div>
    </main>
  );
}
```

- [ ] **Step 7: Make the page reachable**

Without this the route exists but nothing links to it. In `apps/web/app/page.tsx`, inside
`<div className="header-inner">`, immediately after `<StepRail … />`:

```tsx
          <a className="btn btn-quiet btn-small" href="/assignments">
            Assignments
          </a>
```

`.header-inner` is `display: flex; justify-content: space-between`, and `.btn` already sets
`text-decoration: none`, so an anchor styles correctly.

- [ ] **Step 8: Typecheck**

```bash
npm run typecheck --prefix "/Users/speak2gokul01/Projects backup/t-hacks/apps/web"
```
Expected: passes.

- [ ] **Step 9: Verify in the browser**

Start both processes (two terminals, from the repo root):

```bash
cd "/Users/speak2gokul01/Projects backup/t-hacks" && .venv/bin/python -m uvicorn services.api.app.main:app --port 8000
npm run dev --prefix "/Users/speak2gokul01/Projects backup/t-hacks/apps/web"
```

Open `http://localhost:3000`, click **Assignments**, and check in order:

1. The seeded "Rainfall report" brief renders, with the two core tasks visually distinct (blue wash)
   from the three AI-assistable ones.
2. Click "Use the worked example", then "Hand in".
3. **Exactly one question appears**, and it refers to something in the submitted text — the median,
   or the July figure. A generic question about statistics means `prompts/probe.md` is not doing its
   job; the grounding gate would not catch that, because a generic question can still quote a real
   span.
4. The quoted span shown under the question is text you can find in the submission above.
5. Answer it. Two separate scores appear, plus the percentage the answer counted for.
6. Reload and hand in a submission that says only "I used the median." — a thin submission should
   still produce one question, per the prompt's final constraint.

With no API key configured, step 2 returns a 422 whose `detail` is the `ModelNotConfigured`
sentence, rendered in the error banner. The brief still renders — that is the seeded example doing
its job.

- [ ] **Step 10: Commit**

```bash
git add apps/web/app/assignments apps/web/components/AssignmentBrief.tsx \
  apps/web/components/SubmitStep.tsx apps/web/components/ProbeStep.tsx \
  apps/web/components/EvaluationStep.tsx apps/web/app/globals.css apps/web/app/page.tsx
git commit -m "Add the assignment page, the one-question step and the mark view"
```

---

## Self-Review

**Spec coverage**

| Requirement | Task |
|---|---|
| Teacher splits AI-assistable work from the cognitive core | 1 (`TaskMode`, `AssignmentTask`), 5 (seed), 7 (`AssignmentBrief`) |
| Student submits the core work | 1 (`SubmissionRequest`), 5 (`create_submission`), 7 (`SubmitStep`) |
| AI asks **exactly one** question from the cognitive part | 1 (single scalar `question`), 4 (`probe_question`, `prompts/probe.md`), 5 (409 on a second call) |
| The question is grounded in the student's own work | 3 (`check_grounding` + its test), 4 (`quoted_span` in the prompt), 5 (gate before persistence) |
| Student answers it | 1 (`ProbeAnswerRequest`), 5 (`answer_probe`), 7 (`ProbeStep`) |
| The answer is included in the evaluation | 4 (`student_answer` in the payload), 1 (`probe_score`), 5 (`weighted_score` from `settings`) |
| Example test case that asks for the user's answer | 5 (`seed_assignment.py`), 7 ("Use the worked example" + the step 9 walkthrough) |
| Reusable boilerplate | Global constraints hold every new file to the repo's existing shapes; the feature adds no new dependency, no new framework, and touches one line of one existing route |

**Type consistency:** `Assignment`, `AssignmentTask`, `Submission`, `SubmissionProbe`,
`SubmissionEvaluation`, `GeneratedProbe`, `GeneratedEvaluation` defined in Task 1 and used unchanged
in 2–7. `check_grounding`/`GroundingResult`/`MINIMUM_SPAN_WORDS` named identically in Task 3, its
test, and Task 5. `probe_question`/`evaluate_submission` match between Task 4 and the Task 5 routes.
The TS interfaces in Task 6 mirror the Python field names character for character.

**Three risks worth stating plainly:**

1. **The grounding gate proves the span is real, not that the question is good.** A model can quote a
   genuine span and still ask something generic. That failure is invisible to the gate and is caught
   only by reading the output — hence step 9.3. If it recurs, tighten `prompts/probe.md` rather than
   the gate.
2. **`str(error)` reaches `HTTPException(detail=…)` unscrubbed.** Secrets are scrubbed only inside
   `pipeline._fallback_or_fail`, which these synchronous routes do not use. A provider exception
   carrying an API key would surface in the browser. Out of scope here, but do not assume it is
   handled.
3. **The frontend mirror is hand-maintained.** `npm run typecheck` catches a field the TS types
   declare and Python does not, but it cannot catch a field Python added and TS omitted — that
   silently arrives as `undefined`.

---

## Removed from the original plan

Cut because nothing in the feature reads them:

- `GET /api/submissions/{id}` and `api.submission()` — never called; every mutation returns the full
  `Submission` and the page holds it in state.
- `GET /api/assignments/{id}` and `api.assignment()` — never called; the page uses the list route and
  takes `[0]`.
- `GeneratedAssignment` and `GeneratedAssignmentTask` — there is no route that generates an
  assignment, so both models were unreachable. `AssignmentTask` is now a single plain stored model.
- `AssignmentTask.id` and the five hand-written 32-char seed ids — nothing looks a task up or puts
  one in a path.
- `Assignment.generated_live` — carried over from `Storyboard`, read nowhere.
- `focus` on `GeneratedProbe`/`SubmissionProbe` — generated, validated, persisted and mirrored into
  TypeScript, but never rendered. Its bullet is gone from `prompts/probe.md` too.
- `submissionStateLabels` — no component imported it; not one of the four states is displayed.
- `ai_assistable_tasks` in the evaluation payload, and the two prompt bullets defending against
  penalising it — the student only ever hands in `core_response`, so there is nothing to penalise.

Cut as scope, with the trade-off stated:

- **The bundled route test** (a `FakeAssignmentAI`, a temp dir, a 7-kwarg `Settings`, three patched
  globals, ~110 lines). `docs/HANDOFF.md` pins "keep tests minimal"; the grounding gate in Task 3 is
  the only logic here that fails silently. What you give up: automated assertions that a second probe
  409s and that `weighted_score` is `core*(1-w) + probe*w`. Both are visible on one screen of code
  and are exercised by the Task 7 walkthrough.
- **`headingRef` focus management** and the `lastStep` ref that worked around React 19's development
  double-invocation — ~15 lines threaded as a prop through four components. Accessibility polish,
  unrelated to the feature. Add it back after the demo.
- **`ProbeStep`'s `onAnswer: Promise<boolean>`** — it existed so the child could clear its textarea on
  success, but on success the parent unmounts the child. Now `void`.
- **The per-row mode tag in `AssignmentBrief`** — it repeated the group heading directly above it.
- **Manim and `imageio-ffmpeg`** from the Task 0 install; see Task 0 Step 1 for what that costs.

Fixed rather than cut:

- **Every `cd` path.** The original pointed at `/Users/speak2gokul01/projects/t-hacks`, which does not
  exist; the real path differs in case and name and contains a space, so it must be quoted.
- **`uv` and `python3.12` are both absent** on this machine, so Task 0 Step 1 is rewritten.
- **`answer_probe` stranded the student on a marking failure.** It saved `state = ANSWERED` before
  calling the model, then rejected anything but `PROBED` — so every retry after a 422 hit a 409 and
  the submission could never be marked. The guard now accepts `PROBED` or `ANSWERED`.
- **`handIn` orphaned submissions.** It called `submit` then `probe`; a probe failure left the
  submission behind and the next attempt created another. It now reuses the existing submission when
  the draft is unchanged.
- **Nothing linked to `/assignments`.** Task 7 Step 7 adds the link.
