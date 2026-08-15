from __future__ import annotations

from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .ai import AIService, ModelNotConfigured
from .catalog import Catalog
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
from .narration import ElevenLabsNarration
from .pipeline import GenerationPipeline
from .probe import check_grounding
from .rendering import LocalRenderer
from .seed_assignment import SEED_ASSIGNMENT_ID, seed_assignment
from .settings import get_settings
from .storage import Storage

settings = get_settings()
storage = Storage(settings.artifact_root)
catalog = Catalog(settings.catalog_path)
ai = AIService(settings)
narration = ElevenLabsNarration(settings)
renderer = LocalRenderer(settings)
pipeline = GenerationPipeline(settings, storage, catalog, ai, narration, renderer)

# The worked example is written once at import, so the assignment list is never empty
# on a fresh machine and the feature demonstrates with no API key configured. Import
# already touches the filesystem here (Catalog parses its JSON, Storage mkdirs), so a
# write is consistent — but it must never raise, or the app becomes unimportable.
try:
    storage.load_assignment(SEED_ASSIGNMENT_ID)
except FileNotFoundError:
    storage.save_assignment(seed_assignment())

app = FastAPI(title="Klarblick API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "model_configured": settings.model_is_configured,
        "elevenlabs_configured": settings.elevenlabs_is_configured,
    }


@app.get("/api/catalog")
def get_catalog() -> dict[str, object]:
    return catalog.as_dict()


@app.post("/api/storyboards", response_model=Storyboard)
def create_storyboard(request: LessonRequest) -> Storyboard:
    try:
        topic, subtopic = catalog.resolve(request)
        generated, generated_live = ai.create_storyboard(
            request,
            topic,
            subtopic,
            permit_hero_draft=catalog.is_hero(request) and settings.allow_hero_fallback,
        )
    except (ValueError, ModelNotConfigured, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    duration = sum(section.duration_seconds for section in generated.sections)
    if not settings.lesson_min_seconds <= duration <= settings.lesson_max_seconds:
        raise HTTPException(
            status_code=422,
            detail=(
                f"The storyboard draft is {duration:.0f} seconds long, outside the accepted "
                f"{settings.lesson_min_seconds} to {settings.lesson_max_seconds} second range."
            ),
        )
    if not settings.lesson_min_sections <= len(generated.sections) <= settings.lesson_max_sections:
        raise HTTPException(
            status_code=422,
            detail=(
                f"The storyboard draft has {len(generated.sections)} sections, outside the accepted "
                f"{settings.lesson_min_sections} to {settings.lesson_max_sections} range."
            ),
        )

    storyboard = Storyboard(
        id=uuid4().hex,
        request=request,
        title=generated.title,
        learning_objective=generated.learning_objective,
        selected_methods=generated.selected_methods,
        sections=[
            StoryboardSection(id=uuid4().hex, **section.model_dump()) for section in generated.sections
        ],
        recap_cards=generated.recap_cards,
        state=StoryboardState.DRAFT,
        generated_live=generated_live,
    )
    storage.save_storyboard(storyboard)
    return storyboard


@app.post("/api/storyboards/{storyboard_id}/sections/{section_id}/revise", response_model=Storyboard)
def revise_section(storyboard_id: str, section_id: str, request: SectionRevisionRequest) -> Storyboard:
    try:
        storyboard = storage.load_storyboard(storyboard_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Storyboard not found.") from error
    if storyboard.state != StoryboardState.DRAFT:
        raise HTTPException(status_code=409, detail="An approved storyboard can no longer be changed.")
    if not any(section.id == section_id for section in storyboard.sections):
        raise HTTPException(status_code=404, detail="Storyboard section not found.")

    try:
        revised = ai.revise_section(storyboard, section_id, request.comment)
    except (ModelNotConfigured, RuntimeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    storyboard.sections = [
        StoryboardSection(id=section.id, **revised.model_dump()) if section.id == section_id else section
        for section in storyboard.sections
    ]
    storage.save_storyboard(storyboard)
    return storyboard


@app.post("/api/storyboards/{storyboard_id}/approve", response_model=RenderJob)
def approve_storyboard(storyboard_id: str, background_tasks: BackgroundTasks) -> RenderJob:
    try:
        storyboard = storage.load_storyboard(storyboard_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Storyboard not found.") from error
    if storyboard.state != StoryboardState.DRAFT:
        raise HTTPException(status_code=409, detail="The storyboard has already been approved.")

    storyboard.state = StoryboardState.APPROVED
    storage.save_storyboard(storyboard)
    job = RenderJob(
        id=uuid4().hex,
        storyboard_id=storyboard.id,
        status=JobStatus.NARRATING,
        message="Generation has started.",
    )
    storage.save_job(job)
    background_tasks.add_task(pipeline.run, job.id)
    return job


@app.get("/api/jobs/{job_id}", response_model=RenderJob)
def get_job(job_id: str) -> RenderJob:
    try:
        return storage.load_job(job_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Render job not found.") from error


@app.get("/api/jobs/{job_id}/artifacts/{artifact_name}")
def get_artifact(job_id: str, artifact_name: str) -> FileResponse:
    try:
        job = storage.load_job(job_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Render job not found.") from error
    allowed = {artifact.name for artifact in job.artifacts}
    if artifact_name not in allowed:
        raise HTTPException(status_code=404, detail="Artifact not found.")
    path = storage.job_dir(job_id) / "final" / artifact_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="The artifact file is missing.")
    media_type = "video/mp4" if artifact_name.endswith(".mp4") else "image/png"
    return FileResponse(path, media_type=media_type, filename=artifact_name)


@app.get("/api/assignments")
def list_assignments() -> dict[str, object]:
    return {"assignments": [assignment.model_dump() for assignment in storage.list_assignments()]}


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
    except Exception as error:
        # ModelNotConfigured, provider auth failures, network errors — every way the
        # model call can fail reads as one 422 sentence, never a bare 500. Verified
        # against a real 401: openai.AuthenticationError is not a RuntimeError.
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
    except Exception as error:
        # Same mapping as the probe route: any model-call failure is a 422 sentence.
        # The answer was already saved above, so the student can simply retry.
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

