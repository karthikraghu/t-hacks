"""A worked example assignment, so the feature is demoable with no model configured.

The same reason `hero.py` exists. The split here is deliberately unarguable:
computing an average is arithmetic a machine should do, and deciding *which*
average represents the data fairly is the judgement the assignment is about.
"""

from __future__ import annotations

from .models import Assignment, AssignmentTask, TaskMode

#: Fixed, and shaped like `uuid4().hex` so it is safe to interpolate into a path.
SEED_ASSIGNMENT_ID = "5eed0000000000000000000000000001"


def seed_assignment() -> Assignment:
    return Assignment(
        id=SEED_ASSIGNMENT_ID,
        title="Rainfall report",
        brief=(
            "You are given the monthly rainfall for one year in millimetres. Produce a "
            "one-page report: a tidy table, one summary figure for the whole year, and a "
            "short paragraph saying what kind of year it was."
        ),
        tasks=[
            AssignmentTask(
                description="Lay the figures out as a table",
                mode=TaskMode.AI_ASSISTABLE,
                rationale="Formatting is presentation, not mathematics.",
            ),
            AssignmentTask(
                description="Work out the mean, the median and the range",
                mode=TaskMode.AI_ASSISTABLE,
                rationale="The arithmetic is mechanical once the method is chosen.",
            ),
            AssignmentTask(
                description="Draw the bar chart",
                mode=TaskMode.AI_ASSISTABLE,
                rationale="Plotting given numbers adds nothing to the reasoning.",
            ),
            AssignmentTask(
                description=(
                    "Choose which summary figure represents this year fairly, and say why"
                ),
                mode=TaskMode.CORE,
                rationale=(
                    "Deciding between the mean and the median for this data is the "
                    "judgement the assignment is about."
                ),
            ),
            AssignmentTask(
                description="Explain what the one unusual month means for your answer",
                mode=TaskMode.CORE,
                rationale="Reading an outlier is interpretation, not calculation.",
            ),
        ],
        example_response=(
            "Rainfall for the year is in the table. The mean is 74 mm and the median is "
            "58 mm. I used the median as the summary figure for the year. July had 268 mm, "
            "which is much higher than every other month. Overall the year was fairly dry "
            "apart from one wet month."
        ),
    )
