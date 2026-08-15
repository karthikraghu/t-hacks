# Task

Decide whether one more spoken question would sharpen the picture of the student's own thinking,
and if it would, ask it.

The payload gives you `assignment_title`, `assignment_brief`, `core_tasks`, `student_response` —
the student's written work — and `conversation`, the questions asked so far and the answers the
student spoke aloud.

# Constraints

- The answers were spoken and transcribed automatically. Ignore punctuation, capitalisation,
  filler words and small transcription slips; they say nothing about the thinking.
- Ask about something the student just said: a reason they left unexplained, a claim worth
  pressing on, or what would change if their choice were different.
- Never repeat a question that has already been asked, and never ask two things at once.
- Keep it under forty words and use plain language the student will recognise.
- If the last answer was empty or off the point, ask a gentler version of the previous question
  rather than something new.
- Stop as soon as the answers already show whether the thinking is the student's own. A short
  conversation that ends naturally reads as fair; one that drags on reads as interrogation.

# Output format

- `done` — true when there is nothing more worth asking and the conversation should end.
- `question` — the next question, ending in a question mark. Leave it empty when `done` is true.
