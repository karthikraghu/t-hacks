"""The one check this feature needs.

The grounding gate is the only non-obvious logic here, and its failure mode is silent:
a fluent, plausible question about work the student never did looks exactly like a good
one. Everything else in the feature fails loudly or is visible in the browser.
"""

from __future__ import annotations

import unittest

from services.api.app.probe import MINIMUM_SPAN_WORDS, check_grounding


class AssignmentGroundingChecks(unittest.TestCase):
    submission = (
        "Rainfall for the year is in the table. The mean is 74 mm and the median is 58 mm. "
        "I used the median as the summary figure because July had 268 mm."
    )

    def test_span_copied_from_the_submission_is_grounded(self) -> None:
        result = check_grounding("I used the median as the summary figure", self.submission)
        self.assertTrue(result.grounded)
        self.assertEqual([], result.issues)

    def test_span_the_student_never_wrote_is_rejected(self) -> None:
        # The failure the gate exists for. Nothing may be persisted on this path.
        result = check_grounding("I calculated the standard deviation", self.submission)
        self.assertFalse(result.grounded)
        self.assertTrue(any("does not appear" in issue for issue in result.issues))

    def test_whitespace_and_case_differences_still_count_as_grounded(self) -> None:
        # Models reflow whitespace and change capitalisation when quoting. Holding the
        # span to byte equality would reject honest quotes far more often than it would
        # catch invented ones.
        result = check_grounding("  i USED   the median\nas the summary figure ", self.submission)
        self.assertTrue(result.grounded)

    def test_a_span_too_short_to_mean_anything_is_rejected(self) -> None:
        # "the" occurs in every submission ever written. A span that short proves the
        # model quoted nothing in particular.
        result = check_grounding("the", self.submission)
        self.assertFalse(result.grounded)
        self.assertTrue(any(str(MINIMUM_SPAN_WORDS) in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
