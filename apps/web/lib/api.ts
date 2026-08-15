import type { Assignment, Catalog, LessonRequest, RenderJob, Storyboard, Submission } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
    throw new Error(detail || `The request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  catalog: () => request<Catalog>("/api/catalog"),
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
  artifactUrl: (path: string) => `${API_URL}${path}`,
  assignments: () => request<{ assignments: Assignment[] }>("/api/assignments"),
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
  probeAudioUrl: (submissionId: string) => `${API_URL}/api/submissions/${submissionId}/probe/audio`,
};
