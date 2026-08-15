from .models import (
    GeneratedSection,
    GeneratedStoryboard,
    LessonRequest,
    RecapCard,
    TeachingMethod,
)


# Narration length is sized to the declared durations at the measured speaking rate of
# about 13.5 characters per second, so the rendered video really lasts as long as the
# storyboard promises the teacher.
def hero_storyboard(request: LessonRequest) -> GeneratedStoryboard:
    objective = request.objective or (
        "Explain and calculate slope as the ratio of the change in height to the change across."
    )
    return GeneratedStoryboard(
        title="Understanding slope: how steeply does a line rise?",
        learning_objective=objective,
        selected_methods=[TeachingMethod.VISUAL_LINKING, TeachingMethod.WORKED_EXAMPLE],
        sections=[
            GeneratedSection(
                title="A path gets steeper",
                purpose="Everyday starting point",
                narration=(
                    "Picture a path that runs to the right and gains height as it goes. "
                    "Some paths feel gentle, others feel steep. "
                    "How can we describe that steepness with a single number? "
                    "To do it, we compare how far we move across with how far we climb."
                ),
                visual_plan=(
                    "A coordinate system appears. A point moves along a rising line; the horizontal "
                    "movement and the gain in height are labelled separately."
                ),
                on_screen_text=["change across", "change in height"],
                latex=[],
                duration_seconds=16,
            ),
            GeneratedSection(
                title="The slope triangle",
                purpose="Build the graphical picture",
                narration=(
                    "Start at one point on the line and walk three units to the right. "
                    "Now measure how much higher you are: six units. "
                    "Those two movements form a right angled triangle under the line. "
                    "We call it the slope triangle, because it turns steepness into two lengths "
                    "you can read straight off the grid."
                ),
                visual_plan=(
                    "A ValueTracker moves the point from (1, 3) to (4, 9). A labelled triangle shows "
                    "delta x equals 3 and delta y equals 6."
                ),
                on_screen_text=["3 to the right", "6 upwards"],
                latex=["\\Delta x = 3", "\\Delta y = 6"],
                duration_seconds=21,
            ),
            GeneratedSection(
                title="Slope is a ratio",
                purpose="Connect the picture to the formula",
                narration=(
                    "Slope is the change in height divided by the change across. "
                    "Here the height changes by six while we move three units to the right. "
                    "Six divided by three is two. So the slope is two, and that single number "
                    "tells you the line climbs two units for every step you take to the right."
                ),
                visual_plan=(
                    "The slope triangle stays visible. The formula builds up in three large steps, "
                    "with the numerator and denominator each carrying their own text label."
                ),
                on_screen_text=["change in height", "change across", "slope"],
                latex=["m = \\frac{\\Delta y}{\\Delta x}", "m = \\frac{6}{3} = 2"],
                duration_seconds=21,
            ),
            GeneratedSection(
                title="Calculating between two points",
                purpose="Worked example",
                narration=(
                    "Now take two labelled points: A at one, three and B at four, nine. "
                    "First subtract the y values: nine minus three is six. "
                    "Then subtract the x values in the same order: four minus one is three. "
                    "Divide six by three and you get two again. "
                    "Keeping the same order in both subtractions is what keeps the sign correct."
                ),
                visual_plan=(
                    "The two points are labelled. The differences appear one after another before the "
                    "result is highlighted and checked against the graph."
                ),
                on_screen_text=["y difference first", "then x difference", "check the result"],
                latex=["A(1|3)", "B(4|9)", "m = \\frac{9-3}{4-1} = 2"],
                duration_seconds=23,
            ),
            GeneratedSection(
                title="Your turn",
                purpose="Recall and summary",
                narration=(
                    "Remember the rule: slope is the change in height divided by the change across. "
                    "Now here is something to think about. "
                    "If a line climbs twice as high over the same distance across, "
                    "what happens to its slope? Explain your reasoning in one sentence."
                ),
                visual_plan=(
                    "The key formula and a small labelled slope triangle appear. The thinking question "
                    "then stays large and calm on screen."
                ),
                on_screen_text=["What changes?"],
                latex=["m = \\frac{\\Delta y}{\\Delta x}"],
                duration_seconds=18,
                check_prompt=(
                    "Explain in one sentence why doubling the change in height doubles the slope "
                    "when the change across stays the same."
                ),
            ),
        ],
        recap_cards=[
            RecapCard(
                title="Slope as a ratio",
                message="The change in height divided by the change across.",
                visual_plan="Labelled slope triangle mapped onto the numerator and denominator.",
                latex=["m = \\frac{\\Delta y}{\\Delta x}"],
            ),
            RecapCard(
                title="Between two points",
                message="Subtract the coordinates in the same order in both differences.",
                visual_plan="Points A and B in one coordinate system next to the difference formula.",
                latex=["m = \\frac{y_2-y_1}{x_2-x_1}"],
            ),
            RecapCard(
                title="Worked example",
                message="Six units higher over three units to the right gives a slope of two.",
                visual_plan="Graph with a labelled triangle for delta x = 3 and delta y = 6.",
                latex=["m = \\frac{6}{3} = 2"],
            ),
        ],
    )
