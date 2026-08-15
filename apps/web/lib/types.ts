export type Level = "support" | "standard" | "challenge";
export type Method = "auto" | "visual_linking" | "worked_example" | "error_analysis";

export interface Subtopic {
  id: string;
  label: string;
  hero?: boolean;
  default_method?: Method;
  learning_goal?: string;
  misconceptions?: string[];
}

export interface Topic {
  id: string;
  label: string;
  subtopics: Subtopic[];
}

export interface GradeCatalog {
  grade: number;
  topics: Topic[];
}

export interface Catalog {
  notice: string;
  grades: GradeCatalog[];
}

/** One subject pack: its identity and its own catalogue. */
export interface Subject {
  id: string;
  label: string;
  catalog: Catalog;
}

export interface SubjectsResponse {
  subjects: Subject[];
}

export interface LessonRequest {
  subject_id: string;
  grade: number;
  topic_id: string;
  subtopic_id: string;
  level: Level;
  objective?: string;
  method: Method;
}

export interface StoryboardSection {
  id: string;
  title: string;
  purpose: string;
  narration: string;
  visual_plan: string;
  on_screen_text: string[];
  latex: string[];
  duration_seconds: number;
  check_prompt?: string | null;
}

export interface RecapCard {
  title: string;
  message: string;
  visual_plan: string;
  latex: string[];
}

export interface Storyboard {
  id: string;
  request: LessonRequest;
  title: string;
  learning_objective: string;
  selected_methods: Method[];
  sections: StoryboardSection[];
  recap_cards: RecapCard[];
  state: "draft" | "approved";
  generated_live: boolean;
}

export type JobStatus =
  | "planning"
  | "awaiting_approval"
  | "narrating"
  | "coding"
  | "rendering"
  | "checking"
  | "ready"
  | "failed"
  | "cached_fallback";

export interface Artifact {
  name: string;
  kind: "video" | "card";
  url: string;
}

export interface RenderJob {
  id: string;
  storyboard_id: string;
  status: JobStatus;
  attempt_count: number;
  message: string;
  artifacts: Artifact[];
  provenance: "live" | "cached";
  timings_seconds: Record<string, number>;
}

export type TaskMode = "ai_assistable" | "core";
export type SubmissionState = "submitted" | "probed" | "answered" | "evaluated";

export interface AssignmentTask {
  description: string;
  mode: TaskMode;
  rationale: string;
}

export interface Assignment {
  id: string;
  title: string;
  brief: string;
  tasks: AssignmentTask[];
  /** Only the seeded worked example carries one; a real assignment leaves it unset. */
  example_response?: string | null;
}

/** How every assignment is marked. Configuration, so it arrives beside the list. */
export interface Marking {
  probe_weight: number;
  question_limit: number;
}

export interface AssignmentsResponse {
  assignments: Assignment[];
  marking: Marking;
}

export interface SubmissionExchange {
  question: string;
  quoted_span?: string | null;
  answer?: string | null;
}

export interface SubmissionEvaluation {
  core_score: number;
  probe_score: number;
  weighted_score: number;
  probe_weight: number;
  strengths: string[];
  gaps: string[];
  comment: string;
}

export interface Submission {
  id: string;
  assignment_id: string;
  state: SubmissionState;
  core_response: string;
  exchanges: SubmissionExchange[];
  evaluation?: SubmissionEvaluation | null;
}
