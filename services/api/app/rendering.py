from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from .frame_checks import check_frame_bounds
from .models import RendererResult
from .settings import Settings
from .validation import validate_manim_source


class RenderFailure(RuntimeError):
    pass


class LocalRenderer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _job_path(self, job_id: str) -> Path:
        root = self.settings.artifact_root.resolve() / "jobs"
        path = (root / job_id).resolve()
        if root not in path.parents:
            raise RenderFailure("Invalid job directory.")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _clean_environment(self, job_dir: Path) -> dict[str, str]:
        # MiKTeX keeps its package/config indexes in these Windows application-data
        # folders. They are not secrets and are needed even though HOME remains
        # isolated to the job directory.
        allowed = [
            "PATH",
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "PATHEXT",
            "TMP",
            "TEMP",
            "LANG",
            "APPDATA",
            "LOCALAPPDATA",
            "PROGRAMDATA",
        ]
        environment = {key: os.environ[key] for key in allowed if key in os.environ}
        executable_dirs = {
            str(Path(self.settings.manim_command).resolve().parent),
            str(Path(self.settings.ffmpeg_command).resolve().parent),
        }
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            miktex_bin = Path(local_app_data) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64"
            if miktex_bin.exists():
                executable_dirs.add(str(miktex_bin))
        current_path = environment.get("PATH", "")
        environment["PATH"] = os.pathsep.join([*sorted(executable_dirs), current_path])
        environment.update(
            {
                "HOME": str(job_dir),
                "USERPROFILE": str(job_dir),
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        return environment

    def _run(self, command: list[str], job_dir: Path) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                command,
                cwd=job_dir,
                env=self._clean_environment(job_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.settings.render_timeout_seconds,
                check=False,
            )
        except FileNotFoundError as error:
            raise RenderFailure(f"Program not found: {command[0]}") from error
        except subprocess.TimeoutExpired as error:
            raise RenderFailure(f"Rendering was aborted after {self.settings.render_timeout_seconds} seconds.") from error
        if result.returncode != 0:
            details = (result.stderr or result.stdout)[-5000:]
            raise RenderFailure(f"Command failed ({result.returncode}): {details}")
        return result

    def _probe_duration(self, video: Path, job_dir: Path) -> float:
        """Video length in seconds without decoding the full video."""
        try:
            probe = self._run(
                [self.settings.ffmpeg_command, "-i", str(video), "-t", "0", "-f", "null", "-"],
                job_dir,
            )
        except RenderFailure:
            return 0.0
        match = re.search(r"Duration:\s*(\d+):(\d\d):(\d\d(?:\.\d+)?)", probe.stderr or "")
        if not match:
            return 0.0
        hours, minutes, seconds = match.groups()
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)

    @staticmethod
    def _section_midpoints(duration: float, sections: int, section_durations: list[float] | None) -> list[float]:
        """Timestamps in the middle of each real section, away from the fades between them."""
        count = max(sections, 1)
        if section_durations and len(section_durations) == count and sum(section_durations) > 0:
            # Sections differ in length, so an even split lands on transitions and captures
            # a half-faded scene that the visual review then reports as missing content.
            scale = duration / sum(section_durations)
            midpoints = []
            elapsed = 0.0
            for section in section_durations:
                midpoints.append((elapsed + section / 2) * scale)
                elapsed += section
            return midpoints
        return [duration * (index + 0.5) / count for index in range(count)]

    @staticmethod
    def _sync_issues(video_duration: float, section_durations: list[float] | None) -> list[str]:
        """Reject animation that has drifted away from the narration it must match.

        Animations can only be padded with self.wait, never shortened. If a section's
        animations outrun its narration, every later section slides out of sync and FFmpeg
        cuts the tail off when it muxes with -shortest.
        """
        if not section_durations or video_duration <= 0:
            return []
        spoken = sum(section_durations)
        # construct ends with self.wait(1) and each section transition costs about 0.5 s.
        allowance = 1.0 + 0.6 * len(section_durations) + 0.05 * spoken
        if video_duration > spoken + allowance:
            return [
                f"The animation runs {video_duration:.1f} seconds but the narration is only "
                f"{spoken:.1f} seconds long. Picture and sound drift apart and the end of the video is "
                "cut off. Shorten the run_time values in the sections considerably: the sum of all "
                "run_time values in a section must not exceed 60 percent of its duration. "
                "self.wait(remaining) fills the rest of the time."
            ]
        if video_duration < spoken - 1.0:
            return [
                f"The animation is only {video_duration:.1f} seconds long while the narration runs "
                f"{spoken:.1f} seconds, so the audio would be cut off. Pad every section with "
                "self.wait(remaining) up to exactly the duration it was given."
            ]
        return []

    def _extract_frames(
        self,
        video: Path,
        preview_dir: Path,
        job_dir: Path,
        sections: int,
        section_durations: list[float] | None = None,
        duration: float = 0.0,
    ) -> None:
        """One frame near the middle of each section so no section escapes review."""
        count = max(sections, 1)
        if duration <= 0:
            self._run(
                [
                    self.settings.ffmpeg_command,
                    "-y",
                    "-i",
                    str(video),
                    "-vf",
                    "fps=1/20",
                    "-frames:v",
                    str(count),
                    str(preview_dir / "frame_%02d.png"),
                ],
                job_dir,
            )
            return
        for index, timestamp in enumerate(self._section_midpoints(duration, count, section_durations)):
            self._run(
                [
                    self.settings.ffmpeg_command,
                    "-y",
                    "-ss",
                    f"{timestamp:.2f}",
                    "-i",
                    str(video),
                    "-frames:v",
                    "1",
                    str(preview_dir / f"frame_{index + 1:02d}.png"),
                ],
                job_dir,
            )

    @staticmethod
    def _latest(root: Path, pattern: str) -> Path:
        candidates = list(root.rglob(pattern))
        if not candidates:
            raise RenderFailure(f"Expected render artifact is missing: {pattern}")
        return max(candidates, key=lambda item: item.stat().st_mtime)

    def preview(
        self,
        job_id: str,
        code_file: str,
        expected_sections: int,
        section_durations: list[float] | None = None,
    ) -> RendererResult:
        job_dir = self._job_path(job_id)
        code_path = (job_dir / code_file).resolve()
        if job_dir not in code_path.parents or not code_path.exists():
            return RendererResult(success=False, message="The generated Python file is missing or lies outside the job directory.")

        validation = validate_manim_source(code_path.read_text(encoding="utf-8"), expected_sections)
        if not validation.valid:
            return RendererResult(success=False, message="\n".join(validation.issues))

        media_dir = job_dir / "preview_media"
        # Preserve Manim's partial-movie and TeX caches across repair attempts. The
        # generated file is overwritten in place, and Manim hashes each animation's
        # inputs, so unaffected animations can be reused while changed ones rerender.
        media_dir.mkdir(parents=True, exist_ok=True)
        command = [
            self.settings.manim_command,
            "-ql",
            "--media_dir",
            str(media_dir),
            str(code_path),
            "LessonVideo",
        ]
        try:
            self._run(command, job_dir)
            video = self._latest(media_dir, "LessonVideo.mp4")
            preview_dir = job_dir / "preview"
            preview_dir.mkdir(parents=True, exist_ok=True)
            preview_video = preview_dir / "lesson-preview.mp4"
            shutil.copy2(video, preview_video)
            for old in preview_dir.glob("frame_*.png"):
                old.unlink()
            video_duration = self._probe_duration(preview_video, job_dir)
            self._extract_frames(
                preview_video,
                preview_dir,
                job_dir,
                expected_sections,
                section_durations,
                video_duration,
            )
            frames = sorted(preview_dir.glob("frame_*.png"))
            relative_frames = [str(frame.relative_to(job_dir)) for frame in frames]
            # Deterministic gates before the paid visual review: audio drift and cut-off
            # content are both measurable, so neither may depend on a model judgement.
            deterministic_issues = self._sync_issues(video_duration, section_durations) + check_frame_bounds(frames)
            if deterministic_issues:
                return RendererResult(
                    success=False,
                    message="\n".join(deterministic_issues),
                    preview_video=str(preview_video.relative_to(job_dir)),
                    frames=relative_frames,
                )
            return RendererResult(
                success=True,
                message="Preview rendered successfully.",
                preview_video=str(preview_video.relative_to(job_dir)),
                frames=relative_frames,
            )
        except RenderFailure as error:
            return RendererResult(success=False, message=str(error))

    def final(self, job_id: str, code_file: str, expected_sections: int) -> RendererResult:
        job_dir = self._job_path(job_id)
        code_path = (job_dir / code_file).resolve()
        validation = validate_manim_source(code_path.read_text(encoding="utf-8"), expected_sections)
        if not validation.valid:
            return RendererResult(success=False, message="\n".join(validation.issues))

        media_dir = job_dir / "final_media"
        if media_dir.exists():
            shutil.rmtree(media_dir)
        final_dir = job_dir / "final"
        final_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._run(
                [
                    self.settings.manim_command,
                    "-qm",
                    "--disable_caching",
                    "--media_dir",
                    str(media_dir),
                    str(code_path),
                    "LessonVideo",
                ],
                job_dir,
            )
            visual = self._latest(media_dir, "LessonVideo.mp4")
            visual_copy = job_dir / "visual.mp4"
            shutil.copy2(visual, visual_copy)

            class_names = [f"RecapCard{index}" for index in range(1, 4)]
            self._run(
                [
                    self.settings.manim_command,
                    "-qm",
                    "-s",
                    "--disable_caching",
                    "--media_dir",
                    str(media_dir),
                    str(code_path),
                    *class_names,
                ],
                job_dir,
            )

            cards: list[str] = []
            for index, class_name in enumerate(class_names, start=1):
                # Manim CE 0.19 appends its version to still-image filenames
                # (for example RecapCard1_ManimCE_v0.19.0.png).
                rendered = self._latest(media_dir, f"{class_name}*.png")
                destination = final_dir / f"recap_{index}.png"
                shutil.copy2(rendered, destination)
                cards.append(str(destination.relative_to(job_dir)))

            audio = job_dir / "narration.mp3"
            captions = job_dir / "captions.srt"
            if not audio.exists() or not captions.exists():
                raise RenderFailure("The narration or caption file is missing.")

            final_video = final_dir / "lesson.mp4"
            self._run(
                [
                    self.settings.ffmpeg_command,
                    "-y",
                    "-i",
                    "visual.mp4",
                    "-i",
                    "narration.mp3",
                    "-vf",
                    "subtitles=captions.srt:force_style='FontSize=18,Outline=2,Shadow=0,MarginV=10'",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-shortest",
                    "-movflags",
                    "+faststart",
                    str(final_video),
                ],
                job_dir,
            )
            return RendererResult(
                success=True,
                message="Final artifacts rendered successfully.",
                video=str(final_video.relative_to(job_dir)),
                cards=cards,
            )
        except RenderFailure as error:
            return RendererResult(success=False, message=str(error))
