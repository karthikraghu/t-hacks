"""The grounding gate: proof that the question came from the student's own writing.

A follow-up question is only worth asking if it could not have been asked without
reading this particular submission. The model returns the span it quoted, and this
module checks that span really occurs in the student's text before the question is
shown to anyone. Free, deterministic, and run before the result is persisted — the
same shape as `validate_manim_source` and `check_frame_bounds`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Below this a span proves nothing: "the" appears in every submission ever written.
MINIMUM_SPAN_WORDS = 3


@dataclass
class GroundingResult:
    grounded: bool
    issues: list[str] = field(default_factory=list)


def _normalise(text: str) -> str:
    """Lower-case, collapse whitespace, and straighten the quotes models introduce.

    Deliberately forgiving about presentation and strict about words. A model asked
    to copy a span reflows whitespace and changes capitalisation constantly; holding
    it to byte equality would reject honest quotes far more often than it would catch
    invented ones, and a false alarm on every question teaches everyone to ignore it.
    """
    straightened = text.replace("‘", "'").replace("’", "'")
    straightened = straightened.replace("“", '"').replace("”", '"')
    return " ".join(straightened.lower().split())


def check_grounding(quoted_span: str, student_text: str) -> GroundingResult:
    """Return the issues that stop this question being asked. Empty means grounded."""
    issues: list[str] = []
    span = _normalise(quoted_span)
    haystack = _normalise(student_text)
    words = len(span.split())

    if words < MINIMUM_SPAN_WORDS:
        issues.append(
            f"The quoted span is only {words} word(s); at least {MINIMUM_SPAN_WORDS} are "
            "needed to show the question follows the student's own writing."
        )
    elif span not in haystack:
        issues.append(
            "The quoted span does not appear in the submission, so the question was not "
            "drawn from the student's own work."
        )

    return GroundingResult(grounded=not issues, issues=issues)
