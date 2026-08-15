from __future__ import annotations

import base64
import json
from functools import cached_property
from pathlib import Path
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

from .models import (
    Assignment,
    GeneratedEvaluation,
    GeneratedFollowUp,
    GeneratedProbe,
    GeneratedSection,
    GeneratedStoryboard,
    LessonRequest,
    Storyboard,
    StoryboardReview,
    Submission,
    TaskMode,
    VisualReview,
)
from .settings import Settings
from .subjects import SubjectPack, SubjectRegistry


class ModelNotConfigured(RuntimeError):
    pass


class AIService:
    def __init__(self, settings: Settings, subjects: SubjectRegistry) -> None:
        self.settings = settings
        self.subjects = subjects

    @cached_property
    def model(self):  # type: ignore[no-untyped-def]
        if not self.settings.model_is_configured:
            raise ModelNotConfigured(
                "MODEL_NAME and the API key of the selected model provider must be set."
            )
        api_key = (
            self.settings.openai_api_key
            if self.settings.model_provider == "openai"
            else self.settings.anthropic_api_key
        )
        return init_chat_model(
            model=self.settings.model_name,
            model_provider=self.settings.model_provider,
            api_key=api_key,
            base_url=self.settings.openai_base_url or None,
        )

    def prompt(self, name: str) -> str:
        path = self.settings.prompt_root / name
        return path.read_text(encoding="utf-8").strip()

    def lesson_constraints(self) -> dict[str, Any]:
        """Size targets handed to the planner, so lesson length stays configurable."""
        return {
            "sections": self.settings.lesson_target_sections,
            "total_seconds": self.settings.lesson_target_seconds,
            "narration_characters_per_second": 13,
            "recap_cards": 3,
        }

    def storyboard_prompt(self, pack: SubjectPack) -> str:
        # The planner half of the pack's layout vocabulary rides with the storyboard
        # prompt, so the planner only plans section shapes the codegen half can build.
        parts = [
            self.prompt("shared_education.md"),
            pack.subject_prompt(),
            self.prompt("methods.md"),
            pack.methods_prompt(),
            self.prompt("storyboard.md"),
            pack.planner_layouts(),
        ]
        return "\n\n".join(part for part in parts if part)

    def create_storyboard(
        self,
        request: LessonRequest,
        topic: dict[str, Any],
        subtopic: dict[str, Any],
        *,
        permit_hero_draft: bool,
    ) -> tuple[GeneratedStoryboard, bool]:
        pack = self.subjects.pack(request.subject_id)
        if not self.settings.model_is_configured:
            if permit_hero_draft:
                return pack.hero_storyboard(request), False
            raise ModelNotConfigured("This topic requires a configured model.")

        payload = {
            "lesson_request": request.model_dump(mode="json"),
            "topic": topic,
            "subtopic": subtopic,
            "constraints": self.lesson_constraints(),
        }
        planner = self.model.with_structured_output(GeneratedStoryboard, method="json_schema")
        generated = planner.invoke(
            [SystemMessage(content=self.storyboard_prompt(pack)), HumanMessage(content=json.dumps(payload, ensure_ascii=False))]
        )

        reviewer = self.model.with_structured_output(StoryboardReview, method="json_schema")
        review = reviewer.invoke(
            [
                SystemMessage(content="\n\n".join([self.prompt("shared_education.md"), pack.subject_prompt(), self.prompt("review.md")])),
                HumanMessage(content=generated.model_dump_json(indent=2)),
            ]
        )
        if review.approved:
            return generated, True
        if review.corrected_storyboard:
            return review.corrected_storyboard, True
        raise RuntimeError("The internal subject review rejected the draft: " + "; ".join(review.issues))

    def revise_section(self, storyboard: Storyboard, section_id: str, comment: str) -> GeneratedSection:
        section = next(item for item in storyboard.sections if item.id == section_id)
        if not self.settings.model_is_configured:
            raise ModelNotConfigured("Revising a section requires a configured model.")
        context = {
            "lesson_request": storyboard.request.model_dump(mode="json"),
            "learning_objective": storyboard.learning_objective,
            "methods": storyboard.selected_methods,
            "section": section.model_dump(mode="json"),
            "teacher_comment": comment,
        }
        pack = self.subjects.pack(storyboard.request.subject_id)
        model = self.model.with_structured_output(GeneratedSection, method="json_schema")
        return model.invoke(
            [
                SystemMessage(
                    content="\n\n".join(
                        part
                        for part in [
                            self.prompt("shared_education.md"),
                            pack.subject_prompt(),
                            # The rewritten visual plan must stay inside the shapes the
                            # codegen layouts can build, same as the original plan.
                            pack.planner_layouts(),
                            self.prompt("revision.md"),
                        ]
                        if part
                    )
                ),
                HumanMessage(content=json.dumps(context, ensure_ascii=False)),
            ]
        )

    def codegen_prompt(self, storyboard: Storyboard) -> str:
        # Subject prose never reached codegen before packs existed; the codegen half of
        # the pack's layout vocabulary is the one subject-specific thing it needs.
        pack = self.subjects.pack(storyboard.request.subject_id)
        return "\n\n".join([self.prompt("manim_codegen.md"), pack.codegen_layouts()])

    def generate_code(self, storyboard: Storyboard, section_durations: list[float]) -> str:
        if not self.settings.model_is_configured:
            raise ModelNotConfigured("Generating Manim code requires a configured model.")
        payload = {
            "storyboard": storyboard.model_dump(mode="json"),
            "section_durations_seconds": section_durations,
        }
        response = self.model.invoke(
            [SystemMessage(content=self.codegen_prompt(storyboard)), HumanMessage(content=json.dumps(payload, ensure_ascii=False))]
        )
        return self._plain_text(response.content)

    def repair_code(self, code: str, issues: list[str], storyboard: Storyboard, section_durations: list[float]) -> str:
        response = self.model.invoke(
            [
                SystemMessage(content="\n\n".join([self.codegen_prompt(storyboard), self.prompt("repair.md")])),
                HumanMessage(
                    content=json.dumps(
                        {
                            "issues": issues,
                            "storyboard": storyboard.model_dump(mode="json"),
                            "section_durations_seconds": section_durations,
                            "current_code": code,
                        },
                        ensure_ascii=False,
                    )
                ),
            ]
        )
        return self._plain_text(response.content)

    def review_frames(self, storyboard: Storyboard, frame_paths: list[Path]) -> VisualReview:
        if not frame_paths:
            return VisualReview(approved=False, issues=["No review frames were produced."])
        if not self.settings.model_is_configured:
            return VisualReview(approved=True, issues=[])

        pack_rules = self.subjects.pack(storyboard.request.subject_id).review_prompt()
        review_prompt = self.prompt("visual_review.md") + (f"\n\n{pack_rules}" if pack_rules else "")
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": review_prompt + "\n\n" + storyboard.model_dump_json(indent=2),
            }
        ]
        for frame in frame_paths:
            encoded = base64.b64encode(frame.read_bytes()).decode("ascii")
            content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}})
        reviewer = self.model.with_structured_output(VisualReview, method="json_schema")
        return reviewer.invoke([HumanMessage(content=content)])

    def probe_question(self, assignment: Assignment, submission: Submission) -> GeneratedProbe:
        if not self.settings.model_is_configured:
            raise ModelNotConfigured("Asking the follow-up question requires a configured model.")
        context = {
            "assignment_title": assignment.title,
            "assignment_brief": assignment.brief,
            # Only the core tasks. Probing work the assignment allowed to be delegated
            # would tell nobody anything.
            "core_tasks": [
                task.description for task in assignment.tasks if task.mode == TaskMode.CORE
            ],
            # The student's text is a named key in the human turn, never part of the
            # system prompt: it is data, and the rules stay out of its reach.
            "student_response": submission.core_response,
        }
        examiner = self.model.with_structured_output(GeneratedProbe, method="json_schema")
        return examiner.invoke(
            [
                SystemMessage(
                    content="\n\n".join(
                        [self.prompt("shared_education.md"), self.prompt("probe.md")]
                    )
                ),
                HumanMessage(content=json.dumps(context, ensure_ascii=False)),
            ]
        )

    def follow_up_question(
        self, assignment: Assignment, submission: Submission
    ) -> GeneratedFollowUp:
        if not self.settings.model_is_configured:
            raise ModelNotConfigured("Continuing the conversation requires a configured model.")
        context = {
            "assignment_title": assignment.title,
            "assignment_brief": assignment.brief,
            "core_tasks": [
                task.description for task in assignment.tasks if task.mode == TaskMode.CORE
            ],
            "student_response": submission.core_response,
            "conversation": [
                {"question": exchange.question, "answer": exchange.answer or ""}
                for exchange in submission.exchanges
            ],
        }
        examiner = self.model.with_structured_output(GeneratedFollowUp, method="json_schema")
        return examiner.invoke(
            [
                SystemMessage(
                    content="\n\n".join(
                        [self.prompt("shared_education.md"), self.prompt("follow_up.md")]
                    )
                ),
                HumanMessage(content=json.dumps(context, ensure_ascii=False)),
            ]
        )

    def evaluate_submission(
        self, assignment: Assignment, submission: Submission
    ) -> GeneratedEvaluation:
        if not self.settings.model_is_configured:
            raise ModelNotConfigured("Marking a submission requires a configured model.")
        context = {
            "assignment_title": assignment.title,
            "assignment_brief": assignment.brief,
            "core_tasks": [
                task.description for task in assignment.tasks if task.mode == TaskMode.CORE
            ],
            "student_response": submission.core_response,
            "conversation": [
                {"question": exchange.question, "answer": exchange.answer or ""}
                for exchange in submission.exchanges
            ],
        }
        marker = self.model.with_structured_output(GeneratedEvaluation, method="json_schema")
        return marker.invoke(
            [
                SystemMessage(
                    content="\n\n".join(
                        [self.prompt("shared_education.md"), self.prompt("evaluation.md")]
                    )
                ),
                HumanMessage(content=json.dumps(context, ensure_ascii=False)),
            ]
        )

    @staticmethod
    def _plain_text(content: Any) -> str:
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "".join(item.get("text", "") if isinstance(item, dict) else str(item) for item in content)
        else:
            text = str(content)
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            lines = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            text = "\n".join(lines)
            if text.startswith("python\n"):
                text = text[7:]
        return text.strip()
