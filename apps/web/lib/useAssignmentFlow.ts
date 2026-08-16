"use client";

import { useRef, useState } from "react";
import { api } from "./api";
import type { Assignment, Submission } from "./types";

export type AssignmentStep = "write" | "answer" | "marked";

export interface AssignmentFlow {
  submission: Submission | null;
  draft: string;
  setDraft: (value: string) => void;
  step: AssignmentStep;
  busy: boolean;
  error: string | null;
  dismissError: () => void;
  handIn: () => Promise<void>;
  answer: (text: string) => Promise<void>;
}

/* The single owner of the submit → question → mark cycle, shared by the standalone
   assignment demo and the generated learning package so the two cannot drift. Each
   hand-in reuses the current submission when the written work is unchanged. The mark is
   final: there is no retake of the spoken questions once a submission is evaluated. */
export function useAssignmentFlow(assignment: Assignment | null): AssignmentFlow {
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [draft, setDraft] = useState("");
  const [step, setStep] = useState<AssignmentStep>("write");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The text the current submission was created from. Handing in twice after a failed
  // probe reuses that submission instead of orphaning it; editing the work first has to
  // create a new one, because a stored core_response cannot be changed.
  const submittedDraft = useRef<string | null>(null);

  async function handIn() {
    if (!assignment) return;
    setBusy(true);
    setError(null);
    try {
      const text = draft.trim();
      let current = submission;
      if (!current || submittedDraft.current !== text) {
        current = await api.submit(assignment.id, text);
        submittedDraft.current = text;
        setSubmission(current);
      }
      const probed = await api.probe(current.id);
      setSubmission(probed);
      setStep("answer");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The work could not be handed in.");
    } finally {
      setBusy(false);
    }
  }

  async function answer(text: string) {
    if (!submission) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await api.answerProbe(submission.id, text);
      setSubmission(updated);
      // Either the conversation continues with a fresh question, or it is marked.
      if (updated.state === "evaluated") setStep("marked");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The answer could not be marked.");
    } finally {
      setBusy(false);
    }
  }

  return {
    submission,
    draft,
    setDraft,
    step,
    busy,
    error,
    dismissError: () => setError(null),
    handIn,
    answer,
  };
}
