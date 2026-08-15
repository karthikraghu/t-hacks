from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Level(StrEnum):
    SUPPORT = "support"
    STANDARD = "standard"
    CHALLENGE = "challenge"


class TeachingMethod(StrEnum):
    AUTO = "auto"
    VISUAL_LINKING = "visual_linking"
    WORKED_EXAMPLE = "worked_example"
    ERROR_ANALYSIS = "error_analysis"


class StoryboardState(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"


class TaskMode(StrEnum):
    AI_ASSISTABLE = "ai_assistable"
    CORE = "core"


class SubmissionState(StrEnum):
    SUBMITTED = "submitted"
    PROBED = "probed"
    ANSWERED = "answered"
    EVALUATED = "evaluated"


class JobStatus(StrEnum):
    PLANNING = "planning"
    AWAITING_APPROVAL = "awaiting_approval"
    NARRATING = "narrating"
    CODING = "coding"
    RENDERING = "rendering"
    CHECKING = "checking"
    READY = "ready"
    FAILED = "failed"
    CACHED_FALLBACK = "cached_fallback"


class LessonRequest(BaseModel):
    grade: int = Field(ge=5, le=10)
    topic_id: str = Field(min_length=1, max_length=80)
    subtopic_id: str = Field(min_length=1, max_length=80)
    level: Level = Level.STANDARD
    objective: str | None = Field(default=None, max_length=500)
    method: TeachingMethod = TeachingMethod.AUTO

    @field_validator("objective")
    @classmethod
    def trim_objective(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class GeneratedSection(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    purpose: str = Field(min_length=2, max_length=160)
    narration: str = Field(min_length=20, max_length=900)
    visual_plan: str = Field(min_length=10, max_length=800)
    on_screen_text: list[str] = Field(default_factory=list, max_length=6)
    latex: list[str] = Field(default_factory=list, max_length=6)
    duration_seconds: float = Field(ge=6, le=35)
    check_prompt: str | None = Field(default=None, max_length=240)


class StoryboardSection(GeneratedSection):
    id: str


class RecapCard(BaseModel):
    title: str = Field(min_length=2, max_length=100)
    message: str = Field(min_length=4, max_length=260)
    visual_plan: str = Field(min_length=8, max_length=500)
    latex: list[str] = Field(default_factory=list, max_length=5)


class GeneratedStoryboard(BaseModel):
    title: str = Field(min_length=4, max_length=120)
    learning_objective: str = Field(min_length=10, max_length=400)
    selected_methods: list[TeachingMethod] = Field(min_length=1, max_length=2)
    sections: list[GeneratedSection] = Field(min_length=2, max_length=6)
    recap_cards: list[RecapCard] = Field(min_length=3, max_length=3)


class Storyboard(BaseModel):
    id: str
    request: LessonRequest
    title: str
    learning_objective: str
    selected_methods: list[TeachingMethod]
    sections: list[StoryboardSection]
    recap_cards: list[RecapCard]
    state: StoryboardState = StoryboardState.DRAFT
    generated_live: bool = True


class StoryboardReview(BaseModel):
    approved: bool
    issues: list[str] = Field(default_factory=list, max_length=8)
    corrected_storyboard: GeneratedStoryboard | None = None


class SectionRevisionRequest(BaseModel):
    comment: str = Field(min_length=2, max_length=600)


class Artifact(BaseModel):
    name: str
    kind: Literal["video", "card"]
    url: str


class RenderJob(BaseModel):
    id: str
    storyboard_id: str
    status: JobStatus
    attempt_count: int = 0
    message: str
    artifacts: list[Artifact] = Field(default_factory=list)
    provenance: Literal["live", "cached"] = "live"
    timings_seconds: dict[str, float] = Field(default_factory=dict)


class VisualReview(BaseModel):
    approved: bool
    issues: list[str] = Field(default_factory=list, max_length=8)


class RenderPreviewRequest(BaseModel):
    job_id: str
    code_file: str = "lesson.py"


class RenderFinalRequest(RenderPreviewRequest):
    audio_file: str = "narration.mp3"
    captions_file: str = "captions.srt"


class RendererResult(BaseModel):
    success: bool
    message: str
    preview_video: str | None = None
    frames: list[str] = Field(default_factory=list)
    video: str | None = None
    cards: list[str] = Field(default_factory=list)


class AssignmentTask(BaseModel):
    description: str
    mode: TaskMode
    rationale: str


class Assignment(BaseModel):
    id: str
    title: str
    brief: str
    tasks: list[AssignmentTask]
    #: Demo scaffolding: a response the page can drop into the box so the flow can be
    #: shown without typing one. It belongs beside the seeded assignment, not in the
    #: client, because a real assignment simply leaves it unset.
    example_response: str | None = None


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
    # two questions against this schema, which is what makes "one question at a time"
    # structural rather than a prompt instruction the model may drift from.
    question: str = Field(min_length=10, max_length=240)
    quoted_span: str = Field(min_length=4, max_length=200)


class GeneratedFollowUp(BaseModel):
    # `done` rather than a nullable question: both fields stay required, which keeps
    # the schema strict-mode safe, and an accidental empty question cannot silently
    # end the conversation — `done` has to say so explicitly.
    done: bool
    question: str


class SubmissionExchange(BaseModel):
    question: str
    # Only the opening question quotes the written work; follow-ups chase the
    # spoken answers, which are too loosely transcribed to gate on a quote.
    quoted_span: str | None = None
    answer: str | None = None


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
    exchanges: list[SubmissionExchange] = Field(default_factory=list)
    evaluation: SubmissionEvaluation | None = None
