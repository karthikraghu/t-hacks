import json
import shutil
from pathlib import Path
from threading import Lock
from typing import TypeVar

from pydantic import BaseModel

from .models import RenderJob, Storyboard

ModelT = TypeVar("ModelT", bound=BaseModel)


class Storage:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.storyboards = root / "storyboards"
        self.jobs = root / "jobs"
        self._lock = Lock()
        self.storyboards.mkdir(parents=True, exist_ok=True)
        self.jobs.mkdir(parents=True, exist_ok=True)

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

