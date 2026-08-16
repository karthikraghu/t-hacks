import type { JobStatus, Level, Method, TaskMode } from "./types";

export const methodLabels: Record<Method, string> = {
  auto: "Choose for me",
  visual_linking: "Visual linking",
  worked_example: "Worked example",
  error_analysis: "Spot the mistake",
};

export const levelLabels: Record<Level, string> = {
  support: "Supportive",
  standard: "Standard",
  challenge: "Challenging",
};

export const levels: Level[] = ["support", "standard", "challenge"];
export const methods: Method[] = ["auto", "visual_linking", "worked_example", "error_analysis"];

/** The four stages the pipeline actually reports while a job is running. */
export const renderStages: { status: JobStatus; label: string; note: string }[] = [
  { status: "narrating", label: "Narration", note: "voice" },
  { status: "coding", label: "Manim code", note: "scene" },
  { status: "rendering", label: "Render", note: "720p" },
  { status: "checking", label: "Checks", note: "frames" },
];

export const activeStatuses: JobStatus[] = ["narrating", "coding", "rendering", "checking"];

/** Progress, not navigation: neither flow can reopen a step it has left. */
export const lessonSteps = ["Set up", "Script", "Render", "Files"] as const;
export const assignmentSteps = ["Work", "Questions", "Mark"] as const;
/** The student package: the video comes before the same three assignment steps. */
export const learnSteps = ["Watch", "Work", "Questions", "Mark"] as const;

export const taskModeLabels: Record<TaskMode, string> = {
  ai_assistable: "AI may help",
  core: "Your own thinking",
};

/** Core first: the point of the page is what the student has to do themselves. */
export const taskModes: TaskMode[] = ["core", "ai_assistable"];
