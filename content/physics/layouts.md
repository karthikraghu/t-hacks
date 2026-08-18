# Planner

Describe visuals that fit one calm frame, choosing one of three shapes per section:

- A graph section: one coordinate system (time on the x axis) plus at most three labels, each at most
  16 characters, such as "steeper = faster" or "20 m in 4 s". Keep `on_screen_text` for these sections
  to labels of that length.
- A force-diagram section: one body with at most three labelled force arrows. The labels name the
  forces, at most 16 characters each, such as "weight" or "friction".
- A statement section: no diagram, and at most four short lines of text or formulas.

Prefer a graph or force-diagram section whenever the idea can be drawn. Anything about motion, a rate, a
relationship between two quantities, a comparison of two motions, or forces on a body is a diagram section
— the picture builds and moves through the whole narration and is what holds the student's eye. Reserve
statement sections for a formula that has just been shown as a picture, or for the closing recap, and aim
for at least half of the sections — and every section that introduces or develops the core idea — to be
diagram sections. A section that genuinely needs a full explanatory sentence on screen is a statement
section, because a sentence does not fit alongside a diagram; but a short label on a diagram is almost
always better than a sentence with no picture.

# Codegen

Every section uses one of exactly three layouts. Choose per section.

## Layout A: a section with axes

Build the graphic from the axes factory and position it as a whole. Keep every element that belongs to
the graph attached to axis coordinates, so it stays aligned with the axes. The x axis is time.

```python
def section_1(self, duration):
    self.camera.background_color = BG_COLOR
    start = self.time

    heading = Text("The cyclist's journey", font_size=40, color=TEXT_COLOR).to_edge(UP, buff=0.3)
    axes = create_axes().scale(0.83).shift(DOWN * 0.35 + LEFT * 1.2)
    line = axes.plot(lambda t: 2 * t, x_range=[0, 5.2], color=RESULT_COLOR, stroke_width=6)
    run = Line(axes.c2p(1, 2), axes.c2p(4, 2), color=VAR_COLOR, stroke_width=8)
    rise = Line(axes.c2p(4, 2), axes.c2p(4, 8), color=CHANGE_COLOR, stroke_width=8)

    # A point that travels the graph during a ValueTracker sweep keeps the motion
    # visible through the later half of the section, instead of a frozen frame.
    tracker = ValueTracker(0)
    rider = always_redraw(
        lambda: Dot(axes.c2p(tracker.get_value(), 2 * tracker.get_value()),
                    color=RESULT_COLOR).scale(1.1)
    )

    # Every label lives in one column to the right of the axes, so no label can ever
    # land on the line, on a point or on the axis numbers.
    legend = VGroup(
        Text("3 s pass", font_size=30, color=VAR_COLOR),
        Text("6 m covered", font_size=30, color=CHANGE_COLOR),
    ).arrange(DOWN, aligned_edge=LEFT, buff=0.35)
    legend.next_to(axes, RIGHT, buff=0.5)

    # Beats spread through the section, each followed by a short wait so the element
    # lands with its narration; the sweep fills the rest with motion, not a frozen frame.
    self.play(FadeIn(heading), Create(axes), run_time=1.4)
    self.wait(1.5)
    self.play(Create(line), FadeIn(rider), run_time=1.2)
    self.wait(1.5)
    self.play(Create(run), Create(rise), FadeIn(legend), run_time=1.4)
    self.play(tracker.animate.set_value(4), run_time=3.0)

    remaining = duration - (self.time - start)
    self.wait(max(0, remaining))
```

Rules for layout A:

- Place the graphic only with `create_axes().scale(0.83).shift(DOWN * 0.35 + LEFT * 1.2)`, which leaves
  a clear column on the right for the labels.
- Keep axes objects out of `arrange` groups and out of `fit_content`, so a plotted line stays on its
  axes.
- Put **every** label in the single legend column: build a `VGroup` of at most three short lines, each
  at most 16 characters, `arrange(DOWN, aligned_edge=LEFT, buff=0.35)`, then
  `next_to(axes, RIGHT, buff=0.5)`. Colour each legend line to match the element it describes, so the
  reader connects them without a label sitting on the drawing.
- Never place text inside the axes area, on the line, on a point, or under the axis numbers. That is
  what the legend column is for, and it is the one rule that keeps a diagram readable.
- No formula and no sentence belongs in this layout: the heading is directly above the axes and the
  caption band directly below, so there is no room. Give the formula its own layout B section, which is
  the natural shape of a short lesson: one section shows the picture, the next states the formula.

## Layout B: a section without a diagram

Collect the content into one vertical stack, size it once, and animate afterwards.

```python
def section_2(self, duration):
    self.camera.background_color = BG_COLOR
    start = self.time

    heading = Text("Speed is a ratio", font_size=40, color=TEXT_COLOR).to_edge(UP, buff=0.3)
    formula = MathTex(r"v=\frac{s}{t}", color=TEXT_COLOR).scale(1.35)
    words = Text("distance covered divided by time taken", font_size=30, color=MUTED_COLOR)
    example = MathTex(r"v=\frac{6\,\mathrm{m}}{3\,\mathrm{s}}=2\,\mathrm{\frac{m}{s}}", color=RESULT_COLOR).scale(1.3)
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
- Explain a formula on its own line underneath it, as `words` does above. Labels placed beside a
  formula land on top of its numerator or denominator.
- Attach the unit to every number in a `MathTex` with `\mathrm{...}`; a bare number in physics is a
  defect.

## Layout C: a force diagram

One body, force arrows from its centre, and the same legend-column discipline as layout A: the arrows
carry colour, the column carries the words.

```python
def section_3(self, duration):
    self.camera.background_color = BG_COLOR
    start = self.time

    heading = Text("Forces on the crate", font_size=40, color=TEXT_COLOR).to_edge(UP, buff=0.3)
    body = Square(side_length=1.4, color=TEXT_COLOR, fill_opacity=0.15)
    body.move_to(DOWN * 0.35 + LEFT * 2.2)
    weight = Arrow(body.get_center(), body.get_center() + DOWN * 2.0, color=CHANGE_COLOR, stroke_width=8, buff=0)
    normal = Arrow(body.get_center(), body.get_center() + UP * 2.0, color=VAR_COLOR, stroke_width=8, buff=0)

    legend = VGroup(
        Text("weight, down", font_size=30, color=CHANGE_COLOR),
        Text("support, up", font_size=30, color=VAR_COLOR),
    ).arrange(DOWN, aligned_edge=LEFT, buff=0.35)
    legend.next_to(body, RIGHT, buff=2.6)

    # Grow one arrow, wait, then the next, so each force lands with the narration that
    # names it rather than both appearing at once and then holding.
    self.play(FadeIn(heading), FadeIn(body), run_time=1.2)
    self.wait(1.5)
    self.play(GrowArrow(weight), FadeIn(legend[0]), run_time=1.2)
    self.wait(1.5)
    self.play(GrowArrow(normal), FadeIn(legend[1]), run_time=1.2)

    remaining = duration - (self.time - start)
    self.wait(max(0, remaining))
```

Rules for layout C:

- One body only, drawn as a `Square` or `Circle`, placed left of centre inside the content band so the
  legend column fits on the right.
- At most three arrows, each starting at the body's centre with `buff=0`, each at least 1.5 units long
  so the direction is unmistakable, and each in its own colour.
- Every force name lives in the legend column, colour-matched to its arrow, at most 16 characters.
  Never write a label along an arrow.
- Equal forces get equal arrow lengths; a longer arrow must mean a larger force. The drawing is a
  measurement, not a decoration.

## Subject structure

- One shared `create_axes()` factory for the video and the cards. For a motion lesson use
  `x_range=[0, 6, 1]` (time in s), `y_range=[0, 12, 2]` (distance in m), `x_length` about 7.2 and
  `y_length` about 5.0.
- Animate a moving point on a motion graph with `ValueTracker` and `always_redraw`.
