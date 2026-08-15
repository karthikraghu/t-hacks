from manim import *
import numpy as np
import math


VAR_COLOR = "#62D6C5"
CHANGE_COLOR = "#F07D67"
RESULT_COLOR = "#F5C451"
ERROR_COLOR = "#FF6B6B"
BG_COLOR = "#102A31"
TEXT_COLOR = "#F7FAF8"
MUTED_COLOR = "#B8C9C4"
SECTION_DURATIONS = [16, 21, 21, 23, 18]

# The frame spans y = -4.0 to 4.0. The lower band is reserved for the subtitles that
# FFmpeg burns in afterwards, and the upper band belongs to the section heading.
CONTENT_TOP = 2.3
CONTENT_BOTTOM = -3.0
CONTENT_WIDTH = 12.4


def fit_content(group):
    """Scale and centre a section body inside the caption-safe content band."""
    band_height = CONTENT_TOP - CONTENT_BOTTOM
    if group.height > band_height:
        group.scale_to_fit_height(band_height)
    if group.width > CONTENT_WIDTH:
        group.scale_to_fit_width(CONTENT_WIDTH)
    group.move_to(UP * (CONTENT_TOP + CONTENT_BOTTOM) / 2)
    return group


def create_axes():
    axes = Axes(
        x_range=[0, 6, 1],
        y_range=[0, 12, 2],
        x_length=7.2,
        y_length=5.0,
        axis_config={"color": MUTED_COLOR, "include_numbers": True, "font_size": 30},
        tips=False,
    )
    return axes


def transition_out(scene):
    if scene.mobjects:
        scene.play(*[FadeOut(mob) for mob in list(scene.mobjects)], run_time=0.6)


def section_heading(title, subtitle):
    heading = Text(title, font_size=46, color=TEXT_COLOR)
    detail = Text(subtitle, font_size=30, color=MUTED_COLOR).next_to(heading, DOWN, buff=0.22)
    return VGroup(heading, detail).to_edge(UP, buff=0.3)


class LessonVideo(Scene):
    def setup(self):
        self.camera.background_color = BG_COLOR

    def section_1(self, duration):
        heading = section_heading("How steep is this path?", "We compare distance across with height gained.")
        axes = create_axes().scale(0.83).shift(DOWN * 0.35)
        line = axes.plot(lambda x: 2 * x + 1, x_range=[0.5, 5.2], color=RESULT_COLOR, stroke_width=6)
        start = Dot(axes.c2p(1, 3), color=VAR_COLOR).scale(1.15)
        end = Dot(axes.c2p(4, 9), color=CHANGE_COLOR).scale(1.15)
        start_label = Text("Start", font_size=30, color=TEXT_COLOR).next_to(start, LEFT, buff=0.18)
        end_label = Text("Goal", font_size=30, color=TEXT_COLOR).next_to(end, RIGHT, buff=0.18)
        self.play(FadeIn(heading), Create(axes), run_time=1.4)
        self.play(Create(line), FadeIn(start), FadeIn(start_label), run_time=1.2)
        self.play(FadeIn(end), FadeIn(end_label), run_time=0.8)
        used = 3.4
        self.wait(max(duration - used - 0.6, 0))
        transition_out(self)

    def section_2(self, duration):
        heading = section_heading("The slope triangle", "Walk to the right, then measure the height gained.")
        axes = create_axes().scale(0.83).shift(DOWN * 0.35)
        line = axes.plot(lambda x: 2 * x + 1, x_range=[0.5, 5.2], color=RESULT_COLOR, stroke_width=6)
        tracker = ValueTracker(1)
        moving_point = always_redraw(
            lambda: Dot(axes.c2p(tracker.get_value(), 2 * tracker.get_value() + 1), color=CHANGE_COLOR).scale(1.15)
        )
        triangle = always_redraw(
            lambda: Polygon(
                axes.c2p(1, 3),
                axes.c2p(tracker.get_value(), 3),
                axes.c2p(tracker.get_value(), 2 * tracker.get_value() + 1),
                color=VAR_COLOR,
                fill_color=VAR_COLOR,
                fill_opacity=0.12,
                stroke_width=4,
            )
        )
        run_label = Text("3 to the right", font_size=30, color=TEXT_COLOR).move_to(axes.c2p(2.5, 2.35))
        rise_label = Text("6 upwards", font_size=30, color=TEXT_COLOR).move_to(axes.c2p(4.85, 6))
        self.add(axes, line, moving_point, triangle)
        self.play(FadeIn(heading), tracker.animate.set_value(4), run_time=3.0)
        self.play(FadeIn(run_label), FadeIn(rise_label), run_time=1.0)
        used = 4.0
        self.wait(max(duration - used - 0.6, 0))
        transition_out(self)

    def section_3(self, duration):
        heading = section_heading("Slope is a ratio", "Change in height divided by change across.")
        formula = MathTex(r"m=\frac{\Delta y}{\Delta x}", color=TEXT_COLOR).scale(1.35)
        labels = VGroup(
            Text("change in height", font_size=30, color=CHANGE_COLOR),
            Text("change across", font_size=30, color=VAR_COLOR),
        ).arrange(RIGHT, buff=1.1)
        example = MathTex(r"m=\frac{6}{3}=2", color=RESULT_COLOR).scale(1.3)
        result_label = Text("Slope: 2", font_size=34, color=TEXT_COLOR)
        fit_content(VGroup(formula, labels, example, result_label).arrange(DOWN, buff=0.42))
        self.play(FadeIn(heading), Write(formula), run_time=1.5)
        self.play(FadeIn(labels), run_time=0.8)
        self.play(Write(example), FadeIn(result_label), run_time=1.2)
        used = 3.5
        self.wait(max(duration - used - 0.6, 0))
        transition_out(self)

    def section_4(self, duration):
        heading = section_heading("Calculating between two points", "Always take the differences in the same order.")
        points = MathTex(r"A(1|3)\quad B(4|9)", color=TEXT_COLOR).scale(1.2)
        formula = MathTex(r"m=\frac{9-3}{4-1}", color=VAR_COLOR).scale(1.3)
        result = MathTex(r"m=\frac{6}{3}=2", color=RESULT_COLOR).scale(1.3)
        check = Text("Numerator: y difference · Denominator: x difference", font_size=30, color=TEXT_COLOR)
        fit_content(VGroup(points, formula, result, check).arrange(DOWN, buff=0.42))
        self.play(FadeIn(heading), Write(points), run_time=1.3)
        self.play(Write(formula), run_time=1.0)
        self.play(ReplacementTransform(formula.copy(), result), FadeIn(check), run_time=1.2)
        used = 3.5
        self.wait(max(duration - used - 0.6, 0))
        transition_out(self)

    def section_5(self, duration):
        heading = section_heading("Your turn", "Explain the change in your own words.")
        formula = MathTex(r"m=\frac{\Delta y}{\Delta x}", color=RESULT_COLOR).scale(1.4)
        question = Text(
            "What happens to the slope\nif the height doubles?",
            font_size=38,
            color=TEXT_COLOR,
            line_spacing=1.1,
        )
        hint = Text("The distance across stays the same.", font_size=30, color=VAR_COLOR)
        fit_content(VGroup(formula, question, hint).arrange(DOWN, buff=0.55))
        self.play(FadeIn(heading), Write(formula), run_time=1.4)
        self.play(FadeIn(question), FadeIn(hint), run_time=1.1)
        used = 2.5
        self.wait(max(duration - used, 0))

    def construct(self):
        durations = SECTION_DURATIONS
        self.section_1(durations[0])
        self.section_2(durations[1])
        self.section_3(durations[2])
        self.section_4(durations[3])
        self.section_5(durations[4])
        self.wait(1)


class RecapCard1(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        title = Text("Slope as a ratio", font_size=48, color=TEXT_COLOR).to_edge(UP, buff=0.55)
        formula = MathTex(r"m=\frac{\Delta y}{\Delta x}", color=RESULT_COLOR).scale(1.55)
        labels = Text("change in height  ÷  change across", font_size=32, color=TEXT_COLOR)
        labels.next_to(formula, DOWN, buff=0.65)
        self.add(title, formula, labels)


class RecapCard2(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        title = Text("Between two points", font_size=48, color=TEXT_COLOR).to_edge(UP, buff=0.55)
        formula = MathTex(r"m=\frac{y_2-y_1}{x_2-x_1}", color=VAR_COLOR).scale(1.45)
        note = Text("y on top, x below · keep the order", font_size=30, color=TEXT_COLOR)
        note.next_to(formula, DOWN, buff=0.65)
        self.add(title, formula, note)


class RecapCard3(Scene):
    def construct(self):
        self.camera.background_color = BG_COLOR
        title = Text("Example: slope 2", font_size=48, color=TEXT_COLOR).to_edge(UP, buff=0.4)
        axes = create_axes().scale(0.65).shift(DOWN * 0.5 + LEFT * 1.7)
        line = axes.plot(lambda x: 2 * x + 1, x_range=[0.5, 5.2], color=RESULT_COLOR, stroke_width=6)
        triangle = Polygon(
            axes.c2p(1, 3), axes.c2p(4, 3), axes.c2p(4, 9),
            color=VAR_COLOR, fill_color=VAR_COLOR, fill_opacity=0.12, stroke_width=4,
        )
        formula = MathTex(r"m=\frac{6}{3}=2", color=RESULT_COLOR).scale(1.25).move_to(RIGHT * 3.6)
        label = Text("6 up · 3 to the right", font_size=28, color=TEXT_COLOR).next_to(formula, DOWN, buff=0.4)
        self.add(title, axes, line, triangle, formula, label)
