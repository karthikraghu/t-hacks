# Planner

Describe visuals that fit one calm frame, choosing one of two shapes per section:

- A diagram section: a coordinate system plus at most three labels, each at most 16 characters, such as
  "6 up" or "change across". Keep `on_screen_text` for these sections to labels of that length.
- A statement section: no diagram, and at most four short lines of text or formulas.

Prefer a diagram section whenever the idea can be drawn. Anything about a line, a slope, a rate, a
relationship between two quantities, a comparison, or a geometric figure is a diagram section — the
coordinate picture builds and moves through the whole narration and is what holds the student's eye.
Reserve statement sections for a formula that has just been shown as a picture, or for the closing recap,
and aim for at least half of the sections — and every section that introduces or develops the core idea —
to be diagram sections. A section that genuinely needs a full explanatory sentence on screen is a statement
section, because a sentence does not fit alongside a diagram; but a short label on a diagram is almost
always better than a sentence with no picture.

# Codegen

Every section uses one of exactly two layouts. Choose per section.

## Layout A: a section with axes

Build the graphic from the axes factory and position it as a whole. Keep every element that belongs to the
graph attached to axis coordinates, so it stays aligned with the axes.

```python
def section_1(self, duration):
    self.camera.background_color = BG_COLOR
    start = self.time

    heading = Text("How steep is this path?", font_size=40, color=TEXT_COLOR).to_edge(UP, buff=0.3)
    axes = create_axes().scale(0.83).shift(DOWN * 0.35 + LEFT * 1.2)
    line = axes.plot(lambda x: 2 * x + 1, x_range=[0.5, 5.2], color=RESULT_COLOR, stroke_width=6)
    run = Line(axes.c2p(1, 3), axes.c2p(4, 3), color=VAR_COLOR, stroke_width=8)
    rise = Line(axes.c2p(4, 3), axes.c2p(4, 9), color=CHANGE_COLOR, stroke_width=8)

    # A point that rides the line during a ValueTracker sweep keeps the diagram alive
    # through the later half of the section, instead of holding a still frame.
    tracker = ValueTracker(1)
    walker = always_redraw(
        lambda: Dot(axes.c2p(tracker.get_value(), 2 * tracker.get_value() + 1),
                    color=RESULT_COLOR).scale(1.1)
    )

    # Every label lives in one column to the right of the axes, so no label can ever
    # land on the line, on a point or on the axis numbers.
    legend = VGroup(
        Text("3 across", font_size=30, color=VAR_COLOR),
        Text("6 up", font_size=30, color=CHANGE_COLOR),
    ).arrange(DOWN, aligned_edge=LEFT, buff=0.35)
    legend.next_to(axes, RIGHT, buff=0.5)

    # Beats spread through the section, each followed by a short wait so the element
    # lands with its narration; the sweep fills the rest with motion, not a frozen frame.
    self.play(FadeIn(heading), Create(axes), run_time=1.4)
    self.wait(1.5)
    self.play(Create(line), FadeIn(walker), run_time=1.2)
    self.wait(1.5)
    self.play(Create(run), Create(rise), FadeIn(legend), run_time=1.4)
    self.play(tracker.animate.set_value(4), run_time=3.0)

    remaining = duration - (self.time - start)
    self.wait(max(0, remaining))
```

Rules for layout A:

- Place the graphic only with `create_axes().scale(0.83).shift(DOWN * 0.35 + LEFT * 1.2)`, which leaves a
  clear column on the right for the labels.
- Keep axes objects out of `arrange` groups and out of `fit_content`, so a plotted line stays on its axes.
- Put **every** label in the single legend column: build a `VGroup` of at most three short lines, each at
  most 16 characters, `arrange(DOWN, aligned_edge=LEFT, buff=0.35)`, then
  `next_to(axes, RIGHT, buff=0.5)`. Colour each legend line to match the element it describes, so the
  reader connects them without a label sitting on the drawing.
- Never place text inside the axes area, on the line, on a point, inside the triangle, or under the axis
  numbers. That is what the legend column is for, and it is the one rule that keeps a diagram readable.
- No formula and no sentence belongs in this layout: the heading is directly above the axes and the caption
  band directly below, so there is no room. Give the formula its own layout B section, which is the natural
  shape of a short lesson: one section shows the picture, the next states the formula.

## Layout B: a section without axes

Collect the content into one vertical stack, size it once, and animate afterwards.

```python
def section_3(self, duration):
    self.camera.background_color = BG_COLOR
    start = self.time

    heading = Text("Slope is a ratio", font_size=40, color=TEXT_COLOR).to_edge(UP, buff=0.3)
    formula = MathTex(r"m=\frac{\Delta y}{\Delta x}", color=TEXT_COLOR).scale(1.35)
    words = Text("change in height divided by change across", font_size=30, color=MUTED_COLOR)
    example = MathTex(r"m=\frac{6}{3}=2", color=RESULT_COLOR).scale(1.3)
    body = VGroup(formula, words, example).arrange(DOWN, buff=0.42)
    fit_content(body)

    # Reveal one line at a time, with a wait between, so the stack builds with the
    # narration rather than appearing all at once and then holding.
    self.play(FadeIn(heading), Write(formula), run_time=1.5)
    self.wait(1.6)
    self.play(FadeIn(words), run_time=1.0)
    self.wait(1.6)
    self.play(Write(example), run_time=1.2)

    remaining = duration - (self.time - start)
    self.wait(max(0, remaining))
```

Rules for layout B:

- Put at most four elements in the stack, order them with `arrange(DOWN, buff=0.42)`, then call
  `fit_content(...)` on the group.
- Animate only after positioning, and leave individual elements where `arrange` put them.
- Explain a formula on its own line underneath it, as `words` does above. Labels placed beside a formula
  land on top of its numerator or denominator.

## Subject structure

- One shared `create_axes()` factory for the video and the cards. For a slope lesson use
  `x_range=[0, 6, 1]`, `y_range=[0, 12, 2]`, `x_length` about 7.2 and `y_length` about 5.0.
- Animate the slope point and slope triangle with `ValueTracker` and `always_redraw`.
