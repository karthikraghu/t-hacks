import json
import shutil
from pathlib import Path
from threading import Lock
from typing import TypeVar

from pydantic import BaseModel

from .models import Assignment, RenderJob, Storyboard, Submission

ModelT = TypeVar("ModelT", bound=BaseModel)


class Storage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.storyboards = root / "storyboards"
        self.jobs = root / "jobs"
        self.assignments = root / "assignments"
        self.submissions = root / "submissions"
        self.voice = root / "voice"
        self._lock = Lock()
        self.storyboards.mkdir(parents=True, exist_ok=True)
        self.jobs.mkdir(parents=True, exist_ok=True)
        self.assignments.mkdir(parents=True, exist_ok=True)
        self.submissions.mkdir(parents=True, exist_ok=True)
        self.voice.mkdir(parents=True, exist_ok=True)

    def _write(self, path: Path, value: BaseModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(value.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(path)

    def save_storyboard(self, storyboard: Storyboard) -> None:
        with self._lock:
            self._write(self.storyboards / f"{storyboard.id}.json", storyboard)

    def load_storyboard(self, storyboard_id: str) -> Storyboard:
        path = self.storyboards / f"{storyboard_id}.json"
        if not path.exists():
            raise FileNotFoundError(storyboard_id)
        return Storyboard.model_validate_json(path.read_text(encoding="utf-8"))

    def save_job(self, job: RenderJob) -> None:
        with self._lock:
            self._write(self.jobs / job.id / "status.json", job)

    def load_job(self, job_id: str) -> RenderJob:
        path = self.jobs / job_id / "status.json"
        if not path.exists():
            raise FileNotFoundError(job_id)
        return RenderJob.model_validate_json(path.read_text(encoding="utf-8"))

    def job_dir(self, job_id: str) -> Path:
        path = self.jobs / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def copy_fallback(self, fallback_root: Path, job_id: str) -> list[Path]:
        target = self.job_dir(job_id) / "final"
        target.mkdir(parents=True, exist_ok=True)
        required = ["lesson.mp4", "recap_1.png", "recap_2.png", "recap_3.png"]
        copied: list[Path] = []
        for name in required:
            source = fallback_root / name
            if not source.exists():
                raise FileNotFoundError(f"Fallback artifact is missing: {name}")
            destination = target / name
            shutil.copy2(source, destination)
            copied.append(destination)
        return copied

    def cache_fallback(self, fallback_root: Path, job_id: str) -> None:
        source = self.job_dir(job_id) / "final"
        fallback_root.mkdir(parents=True, exist_ok=True)
        for name in ["lesson.mp4", "recap_1.png", "recap_2.png", "recap_3.png"]:
            artifact = source / name
            if artifact.exists():
                shutil.copy2(artifact, fallback_root / name)

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

    def evaluation_audio_path(self, submission_id: str) -> Path:
        # Beside the submission JSON, one spoken result per submission. A submission's
        # evaluation never changes once set, so this is generated once and then served
        # from disk on every replay.
        return self.submissions / f"{submission_id}_result.mp3"

    def save_evaluation_audio(self, submission_id: str, audio: bytes) -> Path:
        path = self.evaluation_audio_path(submission_id)
        with self._lock:
            path.write_bytes(audio)
        return path

    def probe_audio_path(self, submission_id: str, index: int) -> Path:
        # Beside the submission JSON, one file per question, so each spoken question
        # is generated once and then served from disk instead of costing a narration
        # call per replay.
        return self.submissions / f"{submission_id}_probe_{index}.mp3"

    def save_probe_audio(self, submission_id: str, index: int, audio: bytes) -> Path:
        path = self.probe_audio_path(submission_id, index)
        with self._lock:
            path.write_bytes(audio)
        return path

    def thinking_audio_path(self, variant: int, voice_id: str) -> Path:
        # The voice id is part of the name, so changing the conversation voice
        # regenerates the clips instead of serving the old voice from cache.
        return self.voice / f"thinking_{variant}_{voice_id[:8]}.mp3"

    def save_thinking_audio(self, variant: int, voice_id: str, audio: bytes) -> Path:
        path = self.thinking_audio_path(variant, voice_id)
        with self._lock:
            path.write_bytes(audio)
        return path

