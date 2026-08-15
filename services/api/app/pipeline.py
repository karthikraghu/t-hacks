from __future__ import annotations

from threading import Semaphore

from .ai import AIService
from .catalog import Catalog
from .models import Artifact, JobStatus, RenderJob, Storyboard
from .narration import ElevenLabsNarration
from .rendering import LocalRenderer
from .settings import Settings
from .storage import Storage


class GenerationPipeline:
    def __init__(
        self,
        settings: Settings,
        storage: Storage,
        catalog: Catalog,
        ai: AIService,
        narration: ElevenLabsNarration,
        renderer: LocalRenderer,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.catalog = catalog
        self.ai = ai
        self.narration = narration
        self.renderer = renderer
        self._single_job = Semaphore(1)

    def _update(self, job: RenderJob, status: JobStatus, message: str) -> None:
        job.status = status
        job.message = message
        self.storage.save_job(job)

    def run(self, job_id: str) -> None:
        with self._single_job:
            job = self.storage.load_job(job_id)
            storyboard = self.storage.load_storyboard(job.storyboard_id)
            try:
                self._run_live(job, storyboard)
            except Exception as error:  # background boundary: convert to safe job state
                self._fallback_or_fail(job, storyboard, error)

    def _run_live(self, job: RenderJob, storyboard: Storyboard) -> None:
        job_dir = self.storage.job_dir(job.id)

        self._update(job, JobStatus.NARRATING, "Recording the narration for the approved script.")
        narration = self.narration.create(storyboard.sections)
        (job_dir / "narration.mp3").write_bytes(narration.audio)
        (job_dir / "captions.srt").write_text(narration.srt, encoding="utf-8")
        (job_dir / "narration.txt").write_text(narration.text, encoding="utf-8")

        self._update(job, JobStatus.CODING, "Translating the approved storyboard into Manim code.")
        code = self.ai.generate_code(storyboard, narration.section_durations)
        code_path = job_dir / "lesson.py"
        code_path.write_text(code, encoding="utf-8")

        approved = False
        issues: list[str] = []
        attempt_log = job_dir / "attempts.log"
        for attempt in range(3):
            job.attempt_count = attempt
            self._update(job, JobStatus.RENDERING, "Rendering a fast preview.")
            preview = self.renderer.preview(
                job.id,
                code_path.name,
                len(storyboard.sections),
                narration.section_durations,
            )
            if not preview.success:
                issues = [preview.message]
            else:
                self._update(job, JobStatus.CHECKING, "Checking the preview for visible problems.")
                frame_paths = [job_dir / relative for relative in preview.frames]
                review = self.ai.review_frames(storyboard, frame_paths)
                if review.approved:
                    approved = True
                    break
                issues = review.issues

            # Keep every rejection reason on disk. Without it a failed live run leaves no
            # trace of what the render gate or the visual review actually objected to.
            with attempt_log.open("a", encoding="utf-8") as log:
                log.write(f"--- Attempt {attempt + 1} ---\n")
                log.write("\n".join(issues) + "\n")

            if attempt >= 2:
                break
            code = self.ai.repair_code(code, issues, storyboard, narration.section_durations)
            code_path.write_text(code, encoding="utf-8")
            (job_dir / f"lesson_attempt_{attempt + 1}.py").write_text(code, encoding="utf-8")

        if not approved:
            raise RuntimeError("The render check failed after two repair attempts: " + "; ".join(issues))

        self._update(job, JobStatus.RENDERING, "Rendering the final 720p video and three recap cards.")
        result = self.renderer.final(job.id, code_path.name, len(storyboard.sections))
        if not result.success or not result.video or len(result.cards) != 3:
            raise RuntimeError(result.message)

        job.artifacts = [
            Artifact(name="lesson.mp4", kind="video", url=f"/api/jobs/{job.id}/artifacts/lesson.mp4"),
            *[
                Artifact(name=f"recap_{index}.png", kind="card", url=f"/api/jobs/{job.id}/artifacts/recap_{index}.png")
                for index in range(1, 4)
            ],
        ]
        job.provenance = "live"
        self._update(job, JobStatus.READY, "The video and recap cards are ready.")

        # Only seed the fallback when it is missing. The bundled hero is the deliberately
        # polished render from fallback/hero_lesson.py; overwriting it with whatever the last
        # live run happened to produce would quietly degrade the demo safety net.
        if self.catalog.is_hero(storyboard.request):
            bundle = ["lesson.mp4", "recap_1.png", "recap_2.png", "recap_3.png"]
            if not all((self.settings.fallback_root / name).exists() for name in bundle):
                self.storage.cache_fallback(self.settings.fallback_root, job.id)

    def _fallback_or_fail(self, job: RenderJob, storyboard: Storyboard, error: Exception) -> None:
        safe_error = str(error)
        for secret in [
            self.settings.openai_api_key,
            self.settings.anthropic_api_key,
            self.settings.elevenlabs_api_key,
        ]:
            if secret:
                safe_error = safe_error.replace(secret, "[secret]")
        if self.settings.allow_hero_fallback and self.catalog.is_hero(storyboard.request):
            try:
                self.storage.copy_fallback(self.settings.fallback_root, job.id)
                job.artifacts = [
                    Artifact(name="lesson.mp4", kind="video", url=f"/api/jobs/{job.id}/artifacts/lesson.mp4"),
                    *[
                        Artifact(name=f"recap_{index}.png", kind="card", url=f"/api/jobs/{job.id}/artifacts/recap_{index}.png")
                        for index in range(1, 4)
                    ],
                ]
                job.provenance = "cached"
                self._update(
                    job,
                    JobStatus.CACHED_FALLBACK,
                    "Live generation was unavailable, so a prepared demo example is shown instead.",
                )
                return
            except FileNotFoundError:
                pass

        job.provenance = "live"
        concise_error = safe_error if len(safe_error) <= 1200 else "…" + safe_error[-1199:]
        self._update(job, JobStatus.FAILED, f"Generation failed: {concise_error}")
