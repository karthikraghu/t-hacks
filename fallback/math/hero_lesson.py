from manim import *
import numpy as np
import math

BG_COLOR = "#102A31"
TEXT_COLOR = "#F7FAF8"
MUTED_COLOR = "#B8C9C4"
VAR_COLOR = "#62D6C5"
CHANGE_COLOR = "#F07D67"
RESULT_COLOR = "#F5C451"
ERROR_COLOR = "#FF6B6B"

CONTENT_TOP = 2.3
CONTENT_BOTTOM = -3.0
CONTENT_WIDTH = 12.4


def fit_content(group):
    band_height = CONTENT_TOP - CONTENT_BOTTOM
    if group.height > band_height:
        group.scale_to_fit_height(band_height)
    if group.width > CONTENT_WIDTH:
        group.scale_to_fit_width(CONTENT_WIDTH)
    group.move_to(UP * (CONTENT_TOP + CONTENT_BOTTOM) / 2)
    return group


def transition_out(scene):
    if scene.mobjects:
        scene.play(*[FadeOut(mob) for mob in list(scene.mobjects)], run_time=0.5)


DOT_BASE = 0.34
DOT_STEP = 0.42


def make_number_line(length=6.6, shift=DOWN * 0.4 + LEFT * 1.2):
    # A one-dimensional number line, not a 2-D Axes. The data is one-dimensional, so a
    # vertical axis is meaningless; a 2-D Axes here also leaks its axis_config onto the
    # y-axis and draws a stray numbered column up the left. NumberLine draws only the
    # horizontal line and its numbers, which is exactly what a dot plot needs.
    return NumberLine(
        x_range=[0, 8, 1],
        length=length,
        color=MUTED_COLOR,
        stroke_width=3,
        include_numbers=True,
        font_size=28,
    ).shift(shift)


def make_dot_plot(line):
    # One bead per value, sitting on the number line, duplicates stacked upward — a
    # proper dot plot. Order stays 2, 3, 3, 4, 8 so callers can indicate the outlier
    # (dots[-1]) or a median dot (dots[1]).
    values = [2, 3, 3, 4, 8]
    seen = {}
    dots = VGroup()
    for value in values:
        level = seen.get(value, 0)
        seen[value] = level + 1
        color = ERROR_COLOR if value == 8 else VAR_COLOR
        point = line.n2p(value) + UP * (DOT_BASE + level * DOT_STEP)
        dots.add(Dot(point, radius=0.13, color=color))
    return dots


def median_marker(line):
    # A vertical marker rising from the line through the stacked dots at value 3.
    return Line(
        line.n2p(3),
        line.n2p(3) + UP * (DOT_BASE + DOT_STEP + 0.18),
        color=VAR_COLOR,
        stroke_width=7,
    )


def make_row_dots(y=0):
    values = [2, 3, 3, 4, 8]
    dots = VGroup()
    for index, value in enumerate(values):
        x = -4.0 + index * 2.0
        color = ERROR_COLOR if value == 8 else VAR_COLOR
        dots.add(Dot(np.array([x, y, 0]), radius=0.14, color=color))
    return dots


SECTION_DURATIONS = [15.934116569525395, 19.957086594504577, 20.667022481265608, 22.086894254787673, 16.091880099916736]


class LessonVideo(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        self.section_1(SECTION_DURATIONS[0])
        self.section_2(SECTION_DURATIONS[1])
        self.section_3(SECTION_DURATIONS[2])
        self.section_4(SECTION_DURATIONS[3])
        self.section_5(SECTION_DURATIONS[4])
        self.wait(1)

    def section_1(self, duration):
        self.camera.background_color = BG_COLOR
        start = self.time

        heading = Text(
            "A bus-waiting question",
            font_size=40,
            color=TEXT_COLOR,
        ).to_edge(UP, buff=0.3)

        line = make_number_line()
        dots = make_dot_plot(line)
        data = MathTex(
            r"2,\ 3,\ 3,\ 4,\ 8",
            color=TEXT_COLOR,
        ).scale(1.2)
        data.next_to(line, DOWN, buff=0.7)

        legend = VGroup(
            Text("wait minutes", font_size=28, color=MUTED_COLOR),
            Text("usual waits", font_size=28, color=VAR_COLOR),
            Text("one long wait", font_size=28, color=ERROR_COLOR),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.32)
        legend.next_to(line, RIGHT, buff=0.6)

        self.play(FadeIn(heading), Create(line), run_time=1.3)
        self.wait(1.2)
        self.play(FadeIn(dots), Write(data), run_time=1.2)
        self.wait(1.4)
        self.play(FadeIn(legend[0]), run_time=0.8)
        self.wait(1.0)
        self.play(FadeIn(legend[1]), FadeIn(legend[2]), run_time=1.0)
        self.wait(1.0)

        self.play(Indicate(dots[-1], color=ERROR_COLOR, scale_factor=1.35), run_time=1.2)
        self.wait(1.0)

        remaining = duration - (self.time - start)
        self.wait(max(0, remaining))
        transition_out(self)

    def section_2(self, duration):
        self.camera.background_color = BG_COLOR
        start = self.time

        heading = Text(
            "Finding the median",
            font_size=40,
            color=TEXT_COLOR,
        ).to_edge(UP, buff=0.3)

        line = make_number_line()
        dots = make_dot_plot(line)
        ordered = MathTex(
            r"2\ <\ 3\ <\ 3\ <\ 4\ <\ 8",
            color=TEXT_COLOR,
        ).scale(1.15)
        ordered.next_to(line, DOWN, buff=0.7)

        marker = median_marker(line)

        legend = VGroup(
            Text("ordered data", font_size=28, color=TEXT_COLOR),
            Text("middle value", font_size=28, color=VAR_COLOR),
            Text("median", font_size=28, color=VAR_COLOR),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.32)
        legend.next_to(line, RIGHT, buff=0.6)

        median_formula = MathTex(
            r"\tilde{x}=3",
            color=VAR_COLOR,
        ).scale(1.2)
        median_formula.next_to(ordered, DOWN, buff=0.35)

        self.play(FadeIn(heading), Create(line), run_time=1.3)
        self.wait(1.2)
        self.play(FadeIn(dots), Write(ordered), FadeIn(legend[0]), run_time=1.3)
        self.wait(1.5)
        self.play(Create(marker), FadeIn(legend[1]), run_time=1.1)
        self.wait(1.2)
        self.play(Write(median_formula), FadeIn(legend[2]), run_time=1.2)
        self.wait(1.0)
        self.play(Indicate(dots[1], color=VAR_COLOR), run_time=1.0)

        remaining = duration - (self.time - start)
        self.wait(max(0, remaining))
        transition_out(self)

    def section_3(self, duration):
        self.camera.background_color = BG_COLOR
        start = self.time

        heading = Text(
            "Finding the mean",
            font_size=40,
            color=TEXT_COLOR,
        ).to_edge(UP, buff=0.3)

        tracker = ValueTracker(0.0)
        values = [2, 3, 3, 4, 8]

        def animated_dots():
            group = VGroup()
            target = 4.0
            progress = tracker.get_value()
            for index, value in enumerate(values):
                x = -4.0 + index * 2.0
                y = value * (1 - progress) + target * progress
                color = ERROR_COLOR if value == 8 else VAR_COLOR
                group.add(Dot(np.array([x, y * 0.32 - 0.5, 0]), radius=0.14, color=color))
            return group

        visual = VGroup(
            Line(
                LEFT * 4.5 + DOWN * 0.5,
                RIGHT * 4.5 + DOWN * 0.5,
                color=MUTED_COLOR,
                stroke_width=3,
            ),
            always_redraw(animated_dots),
            always_redraw(
                lambda: Line(
                    LEFT * 4.5 + DOWN * 0.5 + UP * (4 * 0.32),
                    RIGHT * 4.5 + DOWN * 0.5 + UP * (4 * 0.32),
                    color=RESULT_COLOR,
                    stroke_width=7,
                )
            ),
            Line(
                LEFT * 1.5 + DOWN * 0.5 + UP * (3 * 0.32),
                RIGHT * 1.5 + DOWN * 0.5 + UP * (3 * 0.32),
                color=VAR_COLOR,
                stroke_width=6,
            ),
        )

        formula = MathTex(
            r"\mu=\frac{2+3+3+4+8}{5}=4",
            color=RESULT_COLOR,
        ).scale(1.2)
        words = Text(
            "equal sharing across five days",
            font_size=30,
            color=MUTED_COLOR,
        )
        median_formula = MathTex(
            r"\tilde{x}=3",
            color=VAR_COLOR,
        ).scale(1.15)

        body = VGroup(visual, formula, words, median_formula).arrange(
            DOWN, buff=0.42
        )
        fit_content(body)

        self.play(FadeIn(heading), FadeIn(visual), run_time=1.4)
        self.wait(1.4)
        self.play(Write(formula), FadeIn(words), run_time=1.4)
        self.wait(1.2)
        self.play(Write(median_formula), run_time=1.0)
        self.wait(1.0)
        self.play(tracker.animate.set_value(1), run_time=4.0)
        self.wait(1.0)

        outlier = Text("outlier", font_size=30, color=ERROR_COLOR)
        outlier.next_to(visual, RIGHT, buff=0.35)
        self.play(FadeIn(outlier), run_time=0.8)
        self.wait(0.8)

        remaining = duration - (self.time - start)
        self.wait(max(0, remaining))
        transition_out(self)

    def section_4(self, duration):
        self.camera.background_color = BG_COLOR
        start = self.time

        heading = Text(
            "One complete calculation",
            font_size=40,
            color=TEXT_COLOR,
        ).to_edge(UP, buff=0.3)

        dots = make_row_dots(y=0)
        baseline = Line(LEFT * 4.7, RIGHT * 4.7, color=MUTED_COLOR, stroke_width=3)
        row = VGroup(baseline, dots)
        brace = Brace(row, DOWN, color=RESULT_COLOR)
        brace_label = Text("sum", font_size=30, color=RESULT_COLOR)
        brace_label.next_to(brace, DOWN, buff=0.18)

        visual = VGroup(row, brace, brace_label)
        sum_formula = MathTex(
            r"2+3+3+4+8=20",
            color=TEXT_COLOR,
        ).scale(1.2)
        mean_formula = MathTex(
            r"\mu=20\div5=4",
            color=RESULT_COLOR,
        ).scale(1.2)
        median_formula = MathTex(
            r"\tilde{x}=3",
            color=VAR_COLOR,
        ).scale(1.2)

        body = VGroup(
            visual,
            sum_formula,
            mean_formula,
            median_formula,
        ).arrange(DOWN, buff=0.42)
        fit_content(body)

        self.play(FadeIn(heading), FadeIn(row), run_time=1.3)
        self.wait(1.2)
        self.play(Create(brace), FadeIn(brace_label), run_time=1.2)
        self.wait(1.1)
        self.play(Write(sum_formula), run_time=1.1)
        self.wait(1.2)
        self.play(Write(mean_formula), run_time=1.1)
        self.wait(1.0)
        self.play(Write(median_formula), run_time=1.1)
        self.wait(1.0)
        self.play(Indicate(dots[-1], color=ERROR_COLOR), run_time=1.0)

        remaining = duration - (self.time - start)
        self.wait(max(0, remaining))
        transition_out(self)

    def section_5(self, duration):
        self.camera.background_color = BG_COLOR
        start = self.time

        heading = Text(
            "Return to the bus",
            font_size=40,
            color=TEXT_COLOR,
        ).to_edge(UP, buff=0.3)

        mean_formula = MathTex(
            r"\mu=4",
            color=RESULT_COLOR,
        ).scale(1.15)
        median_formula = MathTex(
            r"\tilde{x}=3",
            color=VAR_COLOR,
        ).scale(1.15)
        outlier = Text(
            "Outlier: 8 minutes",
            font_size=30,
            color=ERROR_COLOR,
        )
        question = Text(
            "Which is less distorted?",
            font_size=34,
            color=TEXT_COLOR,
        )
        closing = Text(
            "The median is less affected by one large value.",
            font_size=30,
            color=MUTED_COLOR,
        )

        body = VGroup(
            mean_formula,
            median_formula,
            outlier,
            question,
            closing,
        ).arrange(DOWN, buff=0.4)
        fit_content(body)

        self.play(FadeIn(heading), Write(mean_formula), run_time=1.3)
        self.wait(1.3)
        self.play(Write(median_formula), FadeIn(outlier), run_time=1.2)
        self.wait(1.3)
        self.play(FadeIn(question), run_time=1.0)
        self.wait(1.3)
        self.play(FadeIn(closing), run_time=1.0)
        self.wait(1.0)

        remaining = duration - (self.time - start)
        self.wait(max(0, remaining))
        transition_out(self)


class RecapCard1(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Median", font_size=42, color=TEXT_COLOR).to_edge(UP, buff=0.3)
        line = make_number_line(length=6.0, shift=UP * 0.9)
        dots = make_dot_plot(line)
        marker = median_marker(line)
        formula = MathTex(r"2<3<3<4<8", color=TEXT_COLOR).scale(1.1)
        result = MathTex(r"\tilde{x}=3", color=VAR_COLOR).scale(1.2)
        message = Text(
            "Order the data first. The median is the middle value.",
            font_size=30,
            color=MUTED_COLOR,
        )
        message.next_to(line, DOWN, buff=1.0)
        formula.next_to(message, DOWN, buff=0.35)
        result.next_to(formula, DOWN, buff=0.3)

        self.add(title, line, dots, marker, message, formula, result)
        self.wait(2)


class RecapCard2(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Mean", font_size=42, color=TEXT_COLOR).to_edge(UP, buff=0.3)
        dots = make_row_dots(y=-0.3)
        baseline = Line(
            LEFT * 4.7 + DOWN * 0.3,
            RIGHT * 4.7 + DOWN * 0.3,
            color=MUTED_COLOR,
            stroke_width=3,
        )
        mean_line = Line(
            LEFT * 4.7 + UP * 0.98,
            RIGHT * 4.7 + UP * 0.98,
            color=RESULT_COLOR,
            stroke_width=7,
        )
        visual = VGroup(baseline, dots, mean_line)
        formula = MathTex(
            r"\mu=\frac{2+3+3+4+8}{5}=4",
            color=RESULT_COLOR,
        ).scale(1.2)
        message = Text(
            "Add all values and divide by how many values there are.",
            font_size=30,
            color=MUTED_COLOR,
        )
        message.next_to(visual, DOWN, buff=0.65)
        formula.next_to(message, DOWN, buff=0.4)

        self.add(title, visual, message, formula)
        self.wait(2)


class RecapCard3(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR

        title = Text("Outlier effect", font_size=42, color=TEXT_COLOR).to_edge(UP, buff=0.3)
        baseline = Line(LEFT * 4.7, RIGHT * 4.7, color=MUTED_COLOR, stroke_width=3)
        outlier = Dot(np.array([4.0, 1.85, 0]), radius=0.16, color=ERROR_COLOR)
        mean_line = Line(
            LEFT * 4.7 + UP * 0.75,
            RIGHT * 4.7 + UP * 0.75,
            color=RESULT_COLOR,
            stroke_width=7,
        )
        median_line = Line(
            LEFT * 4.7 + UP * 0.15,
            RIGHT * 4.7 + UP * 0.15,
            color=VAR_COLOR,
            stroke_width=7,
        )
        label = Text("8 pulls the mean upward", font_size=30, color=ERROR_COLOR)
        mean_formula = MathTex(r"\mu=4", color=RESULT_COLOR).scale(1.2)
        median_formula = MathTex(r"\tilde{x}=3", color=VAR_COLOR).scale(1.2)
        message = Text(
            "An unusually large value distorts the mean more than the median.",
            font_size=30,
            color=MUTED_COLOR,
        )

        visual = VGroup(baseline, outlier, mean_line, median_line)
        body = VGroup(
            visual,
            label,
            mean_formula,
            median_formula,
            message,
        ).arrange(DOWN, buff=0.35)
        fit_content(body)

        self.add(title, body)
        self.wait(2)