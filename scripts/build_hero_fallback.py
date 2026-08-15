from __future__ import annotations

import re
import sys
from pathlib import Path
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from services.api.app.hero import hero_storyboard  # noqa: E402
from services.api.app.models import LessonRequest, StoryboardSection  # noqa: E402
from services.api.app.narration import ElevenLabsNarration  # noqa: E402
from services.api.app.rendering import LocalRenderer  # noqa: E402
from services.api.app.settings import get_settings  # noqa: E402
from services.api.app.storage import Storage  # noqa: E402


def source_with_durations(source: str, durations: list[float]) -> str:
    if len(durations) != 5:
        raise ValueError("The fixed hero storyboard expects exactly five sections.")
    formatted = ", ".join(f"{duration:.3f}" for duration in durations)
    replacement = f"SECTION_DURATIONS = [{formatted}]"
    updated, count = re.subn(r"^SECTION_DURATIONS\s*=\s*\[[^\]]+\]", replacement, source, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError("SECTION_DURATIONS fehlt in fallback/hero_lesson.py.")
    return updated


def main() -> None:
    settings = get_settings()
    if not settings.elevenlabs_is_configured:
        raise SystemExit("ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID must be set in .env.")

    request = LessonRequest(
        grade=8,
        topic_id="linear-functions",
        subtopic_id="understanding-slope",
        level="standard",
        method="auto",
    )
    generated = hero_storyboard(request)
    sections = [
        StoryboardSection(id=f"hero-{index}", **section.model_dump())
        for index, section in enumerate(generated.sections, start=1)
    ]

    narration = ElevenLabsNarration(settings).create(sections)
    storage = Storage(settings.artifact_root)
    job_id = f"fallback-build-{uuid4().hex[:8]}"
    job_dir = storage.job_dir(job_id)
    (job_dir / "narration.mp3").write_bytes(narration.audio)
    (job_dir / "captions.srt").write_text(narration.srt, encoding="utf-8")
    (job_dir / "narration.txt").write_text(narration.text, encoding="utf-8")

    fixed_source = (settings.fallback_root / "hero_lesson.py").read_text(encoding="utf-8")
    (job_dir / "lesson.py").write_text(
        source_with_durations(fixed_source, narration.section_durations),
        encoding="utf-8",
    )

    renderer = LocalRenderer(settings)
    preview = renderer.preview(job_id, "lesson.py", expected_sections=5)
    if not preview.success:
        raise SystemExit(f"Hero-Vorschau fehlgeschlagen: {preview.message}")
    final = renderer.final(job_id, "lesson.py", expected_sections=5)
    if not final.success or not final.video or len(final.cards) != 3:
        raise SystemExit(f"Hero-Finalrender fehlgeschlagen: {final.message}")

    storage.cache_fallback(settings.fallback_root, job_id)
    print(f"Fallback artifacts created: {settings.fallback_root.resolve()}")
    print(f"Render job for visual inspection: {job_dir.resolve()}")


if __name__ == "__main__":
    main()
