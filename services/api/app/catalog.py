import json
from pathlib import Path
from typing import Any

from .models import LessonRequest


class Catalog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))

    def as_dict(self) -> dict[str, Any]:
        return self.data

    def resolve(self, request: LessonRequest) -> tuple[dict[str, Any], dict[str, Any]]:
        grade = next((item for item in self.data["grades"] if item["grade"] == request.grade), None)
        if not grade:
            raise ValueError("The selected grade is not part of the catalog.")
        topic = next((item for item in grade["topics"] if item["id"] == request.topic_id), None)
        if not topic:
            raise ValueError("The selected topic does not belong to this grade.")
        subtopic = next((item for item in topic["subtopics"] if item["id"] == request.subtopic_id), None)
        if not subtopic:
            raise ValueError("The selected subtopic does not belong to this topic.")
        return topic, subtopic

    def is_hero(self, request: LessonRequest) -> bool:
        _, subtopic = self.resolve(request)
        return bool(subtopic.get("hero"))

