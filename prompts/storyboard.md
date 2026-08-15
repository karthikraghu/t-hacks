# Task

Write a storyboard draft for the lesson data and catalog metadata supplied below.

# Requirements

- Use exactly the number of sections and the total duration given in `constraints`. A short lesson teaches
  one idea well, so keep the scope to what fits that budget instead of adding sections.
- Give each section a distinct purpose, spoken narration, a visual plan Manim can realise, and a duration
  between 6 and 35 seconds. The section durations must add up to the total in `constraints`.
- Size the narration to fill its stated duration. The speech engine delivers about 13 characters, or 2.1
  words, per second, so a 20 second section needs roughly 260 characters, about 42 words. Narration shorter
  than that yields a video noticeably shorter than the duration promised to the teacher.
- Put the wording that appears on screen in `on_screen_text` and mathematical notation in `latex`.
- Describe visuals that fit one calm frame, using only the section shapes defined for this subject at the
  end of this prompt. Choose one shape per section and respect its label limits.
- Plan exactly three recap cards using the same terms, colours and mathematical statements as the video.
- End the final section with a short recall or self-explanation question.
- Base every claim on the supplied metadata; state no curriculum mapping and no properties of individual
  learners.
