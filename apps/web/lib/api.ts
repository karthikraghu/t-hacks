import type {
  AssignmentsResponse,
  LearningPackage,
  LessonRequest,
  RenderJob,
  Storyboard,
  SubjectsResponse,
  Submission,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Carries the HTTP status so a caller can tell, e.g., a 409 "still preparing" from a
    404, without parsing the message. Extends Error, so existing `instanceof Error`
    handling keeps working unchanged. */
export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new Error(`The API at ${API_URL} did not answer. Start it with scripts/start-api.ps1.`);
  }
  if (!response.ok) {
    const body = await response.text();
    let detail = body;
    try {
      const parsed = JSON.parse(body) as { detail?: unknown };
      if (typeof parsed.detail === "string") detail = parsed.detail;
    } catch {
      // Keep a non-JSON response as the useful error message.
    }
    throw new ApiError(response.status, detail || `The request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  subjects: () => request<SubjectsResponse>("/api/subjects"),
  createStoryboard: (lesson: LessonRequest) =>
    request<Storyboard>("/api/storyboards", { method: "POST", body: JSON.stringify(lesson) }),
  reviseSection: (storyboardId: string, sectionId: string, comment: string) =>
    request<Storyboard>(`/api/storyboards/${storyboardId}/sections/${sectionId}/revise`, {
      method: "POST",
      body: JSON.stringify({ comment }),
    }),
  approve: (storyboardId: string) =>
    request<RenderJob>(`/api/storyboards/${storyboardId}/approve`, { method: "POST" }),
  job: (jobId: string) => request<RenderJob>(`/api/jobs/${jobId}`),
  learningPackage: (jobId: string) =>
    request<LearningPackage>(`/api/learning-packages/${jobId}`),
  artifactUrl: (path: string) => `${API_URL}${path}`,
  assignments: () => request<AssignmentsResponse>("/api/assignments"),
  submit: (assignmentId: string, coreResponse: string) =>
    request<Submission>(`/api/assignments/${assignmentId}/submissions`, {
      method: "POST",
      body: JSON.stringify({ core_response: coreResponse }),
    }),
  probe: (submissionId: string) =>
    request<Submission>(`/api/submissions/${submissionId}/probe`, { method: "POST" }),
  answerProbe: (submissionId: string, answer: string) =>
    request<Submission>(`/api/submissions/${submissionId}/answer`, {
      method: "POST",
      body: JSON.stringify({ answer }),
    }),
  probeAudioUrl: (submissionId: string, index: number) =>
    `${API_URL}/api/submissions/${submissionId}/probe/audio/${index}`,
  evaluationAudioUrl: (submissionId: string) =>
    `${API_URL}/api/submissions/${submissionId}/evaluation/audio`,
  // The `v` bump busts any clip a browser cached under the old wording: the URL is
  // otherwise stable, so without it a previously-heard "let me see" replays from cache.
  // Raise it whenever THINKING_LINES change.
  thinkingAudioUrl: (variant: number) => `${API_URL}/api/voice/thinking/${variant}?v=2`,
};
