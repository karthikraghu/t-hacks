from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from services.api.app import main
from services.api.app.catalog import Catalog
from services.api.app.hero import hero_storyboard
from services.api.app.models import (
    GeneratedSection,
    JobStatus,
    LessonRequest,
    RenderJob,
    RendererResult,
    SectionRevisionRequest,
    Storyboard,
    StoryboardSection,
    StoryboardState,
    VisualReview,
)
from services.api.app.narration import NarrationFailure, NarrationPackage
from services.api.app.pipeline import GenerationPipeline
from services.api.app.rendering import LocalRenderer
from services.api.app.settings import REPO_ROOT, Settings
from services.api.app.storage import Storage
from services.api.app.validation import validate_manim_source


class SuccessfulNarration:
    def create(self, sections: list[StoryboardSection]) -> NarrationPackage:
        return NarrationPackage(
            audio=b"test-audio",
            text="\n\n".join(section.narration for section in sections),
            section_durations=[section.duration_seconds for section in sections],
            srt="1\n00:00:00,000 --> 00:00:01,000\nTest\n",
        )


class FailingNarration:
    def create(self, sections: list[StoryboardSection]) -> NarrationPackage:
        raise NarrationFailure("simulierter externer Fehler")


class FakeAI:
    def __init__(self, *, preview_approved: bool = True) -> None:
        self.preview_approved = preview_approved
        self.repair_calls = 0

    def generate_code(self, storyboard: Storyboard, section_durations: list[float]) -> str:
        return (REPO_ROOT / "fallback" / "hero_lesson.py").read_text(encoding="utf-8")

    def review_frames(self, storyboard: Storyboard, frame_paths: list[Path]) -> VisualReview:
        return VisualReview(approved=self.preview_approved, issues=[] if self.preview_approved else ["Vorschau fehlerhaft"])

    def repair_code(
        self,
        code: str,
        issues: list[str],
        storyboard: Storyboard,
        section_durations: list[float],
    ) -> str:
        self.repair_calls += 1
        return code


class SuccessfulRenderer:
    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def preview(
        self,
        job_id: str,
        code_file: str,
        expected_sections: int,
        section_durations: list[float] | None = None,
    ) -> RendererResult:
        return RendererResult(success=True, message="ok", frames=[])

    def final(self, job_id: str, code_file: str, expected_sections: int) -> RendererResult:
        final = self.storage.job_dir(job_id) / "final"
        final.mkdir(parents=True, exist_ok=True)
        (final / "lesson.mp4").write_bytes(b"mp4")
        cards = []
        for index in range(1, 4):
            card = final / f"recap_{index}.png"
            card.write_bytes(b"png")
            cards.append(str(card.relative_to(self.storage.job_dir(job_id))))
        return RendererResult(success=True, message="ok", video="final/lesson.mp4", cards=cards)


class FailingRenderer:
    def __init__(self, leaked_value: str) -> None:
        self.leaked_value = leaked_value

    def preview(
        self,
        job_id: str,
        code_file: str,
        expected_sections: int,
        section_durations: list[float] | None = None,
    ) -> RendererResult:
        return RendererResult(success=False, message=f"Renderfehler {self.leaked_value}")

    def final(self, job_id: str, code_file: str, expected_sections: int) -> RendererResult:
        raise AssertionError("Final render must not run after failed previews")


class MinimalHackathonChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.settings = Settings(
            _env_file=None,
            model_name="",
            artifact_root=root / "runtime",
            catalog_path=REPO_ROOT / "content" / "math" / "catalog.json",
            prompt_root=REPO_ROOT / "prompts",
            fallback_root=root / "fallback",
            manim_command="manim",
            ffmpeg_command="ffmpeg",
        )
        self.storage = Storage(self.settings.artifact_root)
        self.catalog = Catalog(self.settings.catalog_path)
        self.request = LessonRequest(
            grade=8,
            topic_id="linear-functions",
            subtopic_id="understanding-slope",
            level="standard",
            method="auto",
        )
        generated = hero_storyboard(self.request)
        self.storyboard = Storyboard(
            id=uuid4().hex,
            request=self.request,
            title=generated.title,
            learning_objective=generated.learning_objective,
            selected_methods=generated.selected_methods,
            sections=[StoryboardSection(id=uuid4().hex, **section.model_dump()) for section in generated.sections],
            recap_cards=generated.recap_cards,
            state=StoryboardState.DRAFT,
            generated_live=False,
        )
        self.storage.save_storyboard(self.storyboard)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _job(self) -> RenderJob:
        job = RenderJob(
            id=uuid4().hex,
            storyboard_id=self.storyboard.id,
            status=JobStatus.NARRATING,
            message="started",
        )
        self.storage.save_job(job)
        return job

    def test_hero_storyboard_revision_and_artifact_contract(self) -> None:
        original_ids = [section.id for section in self.storyboard.sections]
        target = self.storyboard.sections[1]
        revised = GeneratedSection(**{**target.model_dump(exclude={"id"}), "title": "Revised on purpose"})

        with patch.object(main, "storage", self.storage), patch.object(
            main.ai, "revise_section", return_value=revised
        ):
            result = main.revise_section(
                self.storyboard.id,
                target.id,
                SectionRevisionRequest(comment="Please make this section clearer."),
            )

        self.assertEqual(original_ids, [section.id for section in result.sections])
        self.assertEqual("Revised on purpose", result.sections[1].title)
        self.assertEqual(self.storyboard.sections[0].model_dump(), result.sections[0].model_dump())

        result.state = StoryboardState.APPROVED
        self.storage.save_storyboard(result)
        job = self._job()
        pipeline = GenerationPipeline(
            self.settings,
            self.storage,
            self.catalog,
            FakeAI(),
            SuccessfulNarration(),
            SuccessfulRenderer(self.storage),
        )
        pipeline.run(job.id)
        completed = self.storage.load_job(job.id)
        self.assertEqual(JobStatus.READY, completed.status)
        self.assertEqual(["lesson.mp4", "recap_1.png", "recap_2.png", "recap_3.png"], [a.name for a in completed.artifacts])

    def test_unsafe_code_repair_limit_and_secret_scrubbing(self) -> None:
        unsafe = """
from manim import *
class LessonVideo(Scene):
    def section_1(self, duration):
        open('leak.txt', 'w')
        formula = MathTex(r'\\mathrm{gegen}')
        SurroundingRectangle(formula[4])
        formula.__class__.__init__.__globals__['x']
    def construct(self):
        self.section_1(10)
        self.wait(1)
class RecapCard1(Scene): pass
class RecapCard2(Scene): pass
class RecapCard3(Scene): pass
"""
        validation = validate_manim_source(unsafe, expected_sections=1)
        self.assertFalse(validation.valid)
        self.assertTrue(any("open" in issue for issue in validation.issues))
        self.assertTrue(any("MathTex must not be split" in issue for issue in validation.issues))
        self.assertTrue(any("Prose inside LaTeX" in issue for issue in validation.issues))
        self.assertTrue(any("internal attributes" in issue for issue in validation.issues))

        secret = "unit-test-secret"
        self.settings.openai_api_key = secret
        environment = LocalRenderer(self.settings)._clean_environment(self.storage.job_dir("env-check"))
        self.assertNotIn("OPENAI_API_KEY", environment)
        self.assertNotIn(secret, environment.values())

        self.settings.allow_hero_fallback = False
        self.storyboard.state = StoryboardState.APPROVED
        self.storage.save_storyboard(self.storyboard)
        job = self._job()
        ai = FakeAI(preview_approved=False)
        pipeline = GenerationPipeline(
            self.settings,
            self.storage,
            self.catalog,
            ai,
            SuccessfulNarration(),
            FailingRenderer(secret),
        )
        pipeline.run(job.id)
        failed = self.storage.load_job(job.id)
        self.assertEqual(JobStatus.FAILED, failed.status)
        self.assertEqual(2, ai.repair_calls)
        self.assertNotIn(secret, failed.message)

    def test_frame_bounds_gate_flags_cut_off_content(self) -> None:
        from PIL import Image, ImageDraw

        from services.api.app.frame_checks import check_frame_bounds

        directory = Path(self.temporary.name) / "frames"
        directory.mkdir()

        clean = directory / "frame_01.png"
        image = Image.new("RGB", (854, 480), (16, 42, 49))
        ImageDraw.Draw(image).rectangle([200, 120, 650, 300], fill=(247, 250, 248))
        image.save(clean)

        cut_off = directory / "frame_02.png"
        image = Image.new("RGB", (854, 480), (16, 42, 49))
        # A block running past the lower frame edge, as an overflowing formula stack does.
        ImageDraw.Draw(image).rectangle([200, 400, 650, 480], fill=(247, 250, 248))
        image.save(cut_off)

        # A heading resting near the top edge leaves a few anti-aliased pixels in the band.
        # This must stay approved: an over-tight threshold rejects good frames and burns
        # the two repair attempts on nothing.
        near_edge = directory / "frame_03.png"
        image = Image.new("RGB", (854, 480), (16, 42, 49))
        ImageDraw.Draw(image).rectangle([300, 0, 340, 0], fill=(247, 250, 248))
        image.save(near_edge)

        self.assertEqual([], check_frame_bounds([clean]))
        self.assertEqual([], check_frame_bounds([near_edge]))
        issues = check_frame_bounds([cut_off])
        self.assertTrue(any("caption band" in issue for issue in issues))
        self.assertTrue(any("section_1" in issue for issue in issues))

    def test_cached_hero_fallback_is_labeled(self) -> None:
        self.settings.fallback_root.mkdir(parents=True)
        for name in ["lesson.mp4", "recap_1.png", "recap_2.png", "recap_3.png"]:
            (self.settings.fallback_root / name).write_bytes(name.encode("ascii"))

        self.storyboard.state = StoryboardState.APPROVED
        self.storage.save_storyboard(self.storyboard)
        job = self._job()
        pipeline = GenerationPipeline(
            self.settings,
            self.storage,
            self.catalog,
            FakeAI(),
            FailingNarration(),
            SuccessfulRenderer(self.storage),
        )
        pipeline.run(job.id)
        cached = self.storage.load_job(job.id)
        self.assertEqual(JobStatus.CACHED_FALLBACK, cached.status)
        self.assertEqual("cached", cached.provenance)
        self.assertEqual(4, len(cached.artifacts))
        self.assertIn("prepared demo example", cached.message)


if __name__ == "__main__":
    unittest.main()
