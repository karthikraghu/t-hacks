# Generated Lesson → Assignment → Test Flow

## Summary

Create one automatically generated learning package:

`Watch video → Complete assignment → Answer spoken questions → View mark`

The assignment is generated with the storyboard, linked to the finished render, and exposed through an anonymous lesson-specific URL such as `/learn/{job_id}`. The existing `/assignments` demo remains unchanged.

## Implementation Changes

- Extend storyboard generation to return a validated assignment containing:

  - A self-contained brief aligned with the lesson objective.
  - A new example/problem rather than repeating the video’s worked example.
  - Three to five text-answerable tasks, including at least two `core` reasoning tasks.
  - Any supporting/mechanical tasks marked `ai_assistable`.
  - All required numbers and context—no external worksheets or uploads.

- Have the existing subject reviewer validate both the storyboard and assignment. Add matching assignments to the prepared maths and physics hero storyboards so fallback generation remains complete.

- Persist the generated assignment using the storyboard ID as its assignment ID. Add an optional `storyboard_id` to `Assignment`; it remains empty for the seeded standalone assignment.

- Keep generated assignments out of the existing `GET /api/assignments` response so `/assignments` continues to open the Rainfall report demo.

- Publish a package only when its render job reaches `ready` or `cached_fallback`. Assignment generation failure therefore stops storyboard creation before an expensive render begins.

## Interfaces and Student Experience

- Add `GET /api/learning-packages/{job_id}` returning:

  - Package/job ID and provenance.
  - Lesson title and learning objective.
  - Video artifact and three recap-card artifacts.
  - Linked assignment.
  - Existing marking configuration.

- Return `404` for an unknown job or missing linked assignment and `409` while rendering is incomplete. Existing historical jobs without assignments remain video-only and are not migrated.

- Add `/learn/[jobId]` with the progress rail:

  `Watch · Work · Questions · Mark`

- Watch:

  - Show the lesson objective, video, and recap cards.
  - Use an explicit “I’ve watched this — start the assignment” action; do not enforce player watch time.

- Work:

  - Reuse `AssignmentBrief` and the text-response submission UI.
  - Provide the video and recap cards inside a collapsible “Lesson resources” section.
  - On hand-in, create an immutable submission and request the first grounded question.

- Questions and Mark:

  - Reuse the existing spoken adaptive questions, follow-up limit, grounding gate, weighted evaluation, and feedback components.
  - Add “Try again” after marking; this creates a fresh submission while preserving the previous server-side attempt.

- Add “Open student package” and “Copy package link” actions to the teacher’s finished-files screen.

- Extract the shared assignment state/API behavior into a reusable controller so the generated package and standalone demo cannot drift.

## Test Plan

- Validate live and prepared storyboards contain a self-contained assignment with the required core tasks.
- Verify storyboard creation persists the linked assignment without changing standalone assignment ordering.
- Verify package retrieval is blocked before render completion and returns the correct video, cards, assignment, marking rules, and cached provenance afterward.
- Exercise the linked assignment through submission, grounded probe, follow-up/evaluation, and a second fresh attempt.
- Confirm unknown, incomplete, legacy-without-assignment, and missing-artifact package states produce clear errors.
- Run the existing Python suite, web typecheck, production build, and a browser smoke test covering the complete four-step student journey.

## Assumptions

- V1 remains a local anonymous demo with no accounts, roster, teacher results dashboard, uploads, or cross-device recovery.
- “Simplest way” means fully automatic assignment creation and restarting the student UI after a refresh; stored submissions remain immutable but are not automatically recovered.
- The existing uncommitted physics storyboard, storyboard-prompt, and timing changes must be preserved and extended rather than reverted.
- The visual treatment stays consistent with the current application; the meaningful ordered progress rail is the signature element rather than introducing a separate student design system.
