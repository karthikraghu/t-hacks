# Task

Write a storyboard draft for the lesson data and catalog metadata supplied below.

# Requirements

- Use exactly the number of sections and the total duration given in `constraints`. The lesson still
  teaches exactly one idea; the budget buys depth on that idea, never a second topic.
- Shape the sections as one arc that a teacher would recognise: open with a concrete hook the students
  know from everyday life, build the concept from the hook, formalise it, carry it through one worked
  example, and reserve the whole final section for the closure. Each section must hand over to the
  next — name what returns from the previous section or what the next one will resolve, so the lesson
  reads as one story rather than a list of slides.
- Give each section a distinct purpose, spoken narration, a visual plan Manim can realise, and a duration
  between 12 and 35 seconds. The section durations must add up to the total in `constraints`.
- Size the narration to fill its stated duration. The speech engine delivers about 13 characters, or 2.1
  words, per second, so a 20 second section needs roughly 260 characters, about 42 words. Narration shorter
  than that yields a video noticeably shorter than the duration promised to the teacher.
- Put the wording that appears on screen in `on_screen_text` and mathematical notation in `latex`.
- Describe visuals that fit one calm frame, using only the section shapes defined for this subject at the
  end of this prompt. Choose one shape per section and respect its label limits. Prefer a diagram or graph
  section whenever the idea can be drawn — a line, a rate, a relationship, a comparison, or a figure — so a
  built, moving picture carries the narration rather than a static block of text. Reserve text-only
  statement sections for a formula that has just been shown as a picture, or for the closing recap. Aim for
  at least half of the sections, and every section that introduces or develops the core idea, to be visual
  ones; a visual plan reading "state the formula" for a graphable idea is the thing to avoid.
- Plan exactly three recap cards using the same terms, colours and mathematical statements as the video.
- The final section is the closure, and it does three things in order: it returns to the opening hook and
  states the takeaway in one or two sentences using the exact terms taught; it poses one short recall or
  self-explanation question and leaves a beat of silence for thinking; and it ends on a calm closing
  sentence that tells the student what they can now do. A lesson that stops dead after the question feels
  cut off — the closing sentence is not optional.
- Base every claim on the supplied metadata; state no curriculum mapping and no properties of individual
  learners.

# The assignment

Alongside the storyboard, write one short assignment the student does after watching, in the `assignment`
field. It is what turns a lesson they watched into work they own.

- Give it a `title` and a self-contained `brief`. The brief must carry every number and every piece of
  context the student needs — no external worksheet, upload, or figure they do not already have.
- Set a fresh example or problem. Do not re-use the worked example from the video; the point is to apply
  the idea to something new, not to repeat what was just shown.
- Write three to five `tasks`. Each has a one-line `description`, a `mode`, and a one-line `rationale`
  for that mode.
- Mark a task `ai_assistable` when it is mechanical once the method is chosen — formatting, plotting, or
  arithmetic a machine should do. Mark it `core` when it is the reasoning or judgement the lesson is
  about: choosing between options, interpreting a result, or explaining why.
- At least two tasks must be `core`. Those are the parts the student hands in and is questioned on, so a
  thin core leaves nothing worth asking about. Keep the core tasks answerable in writing, with no diagram
  or upload required.
