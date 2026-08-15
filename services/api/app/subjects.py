"""Subject packs: everything one subject contributes, loaded from content/<subject>/.

A pack is data only — catalogue, prose, and a hero storyboard as JSON validated through
the same Pydantic models. Deliberately no Python and no influence over the validator's
import allowlist: widening `ALLOWED_IMPORT_ROOTS` stays a code change a human reads,
or adding a subject becomes an escalation path into the render subprocess.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import GeneratedStoryboard, LessonRequest

#: The heading that separates the planner-facing half of layouts.md from the
#: codegen-facing half. One file, so the two halves cannot drift apart in separate
#: edits; a fixed heading, so the split never depends on prose.
_CODEGEN_HEADING = "# Codegen"
_PLANNER_HEADING = "# Planner"


class SubjectPack:
    def __init__(self, root: Path) -> None:
        self.root = root
        meta = json.loads((root / "pack.json").read_text(encoding="utf-8"))
        self.id: str = meta["id"]
        self.label: str = meta["label"]
        self.catalog: dict[str, Any] = json.loads((root / "catalog.json").read_text(encoding="utf-8"))

        layouts = (root / "layouts.md").read_text(encoding="utf-8")
        if _PLANNER_HEADING not in layouts or _CODEGEN_HEADING not in layouts:
            raise ValueError(
                f"content/{self.id}/layouts.md must contain the headings "
                f"'{_PLANNER_HEADING}' and '{_CODEGEN_HEADING}'."
            )
        planner, codegen = layouts.split(_CODEGEN_HEADING, 1)
        self._planner_layouts = planner.replace(_PLANNER_HEADING, "# Section shapes for this subject", 1).strip()
        self._codegen_layouts = ("# Section layouts for this subject\n" + codegen).strip()

    def _prose(self, name: str) -> str:
        path = self.root / name
        return path.read_text(encoding="utf-8").strip() if path.exists() else ""

    def subject_prompt(self) -> str:
        return self._prose("subject.md")

    def methods_prompt(self) -> str:
        return self._prose("methods.md")

    def review_prompt(self) -> str:
        return self._prose("review.md")

    def planner_layouts(self) -> str:
        return self._planner_layouts

    def codegen_layouts(self) -> str:
        return self._codegen_layouts

    def resolve(self, request: LessonRequest) -> tuple[dict[str, Any], dict[str, Any]]:
        grade = next((item for item in self.catalog["grades"] if item["grade"] == request.grade), None)
        if not grade:
            raise ValueError("The selected grade is not part of this subject's catalog.")
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

    def hero_storyboard(self, request: LessonRequest) -> GeneratedStoryboard:
        """The pack's prepared storyboard, with the teacher's objective honoured.

        Stored as JSON and validated through the same models as a live draft, so a
        pack cannot ship a storyboard shape the rest of the pipeline would choke on.
        """
        data = json.loads((self.root / "hero_storyboard.json").read_text(encoding="utf-8"))
        generated = GeneratedStoryboard.model_validate(data)
        if request.objective:
            generated.learning_objective = request.objective
        return generated


class SubjectRegistry:
    def __init__(self, content_root: Path) -> None:
        self.packs: dict[str, SubjectPack] = {}
        for entry in sorted(content_root.iterdir()):
            if (entry / "pack.json").exists():
                pack = SubjectPack(entry)
                self.packs[pack.id] = pack
        if not self.packs:
            raise ValueError(f"No subject packs found under {content_root}.")

    def pack(self, subject_id: str) -> SubjectPack:
        pack = self.packs.get(subject_id)
        if not pack:
            raise ValueError("The selected subject is not installed.")
        return pack

    def default_pack(self) -> SubjectPack:
        # Math is the founding subject and the stable default for the /api/catalog alias.
        return self.packs.get("math") or next(iter(self.packs.values()))

    def resolve(self, request: LessonRequest) -> tuple[SubjectPack, dict[str, Any], dict[str, Any]]:
        pack = self.pack(request.subject_id)
        topic, subtopic = pack.resolve(request)
        return pack, topic, subtopic

    def is_hero(self, request: LessonRequest) -> bool:
        return self.pack(request.subject_id).is_hero(request)

    def as_list(self) -> list[dict[str, Any]]:
        return [
            {"id": pack.id, "label": pack.label, "catalog": pack.catalog}
            for pack in self.packs.values()
        ]
