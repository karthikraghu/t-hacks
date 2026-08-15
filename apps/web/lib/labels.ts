import type { JobStatus, Level, Method } from "./types";

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
