"use client";

import { useEffect, useRef, useState } from "react";
import { AssignmentBrief } from "@/components/AssignmentBrief";
import { EvaluationStep } from "@/components/EvaluationStep";
import { ProbeStep } from "@/components/ProbeStep";
import { SubmitStep } from "@/components/SubmitStep";
import { api } from "@/lib/api";
import type { Assignment, Submission } from "@/lib/types";

type Step = "write" | "answer" | "marked";

const EXAMPLE =
  "Rainfall for the year is in the table. The mean is 74 mm and the median is 58 mm. " +
  "I used the median as the summary figure for the year. July had 268 mm, which is much " +
  "higher than every other month. Overall the year was fairly dry apart from one wet month.";

export default function AssignmentsPage() {
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [draft, setDraft] = useState("");
  const [step, setStep] = useState<Step>("write");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The text the current submission was created from. Handing in twice after a failed
  // probe reuses that submission instead of orphaning it; editing the work first has
  // to create a new one, because a stored core_response cannot be changed.
  const submittedDraft = useRef<string | null>(null);

  useEffect(() => {
    api
      .assignments()
      .then((body) => setAssignment(body.assignments[0] ?? null))
      .catch((reason) =>
        setError(reason instanceof Error ? reason.message : "The assignments could not be loaded."),
      );
  }, []);

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
      const marked = await api.answerProbe(submission.id, text);
      setSubmission(marked);
      setStep("marked");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The answer could not be marked.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="main">
      <div className="shell stack">
        {error && (
          <div className="alert alert-error" role="alert">
            <p>{error}</p>
            <button className="btn btn-plain btn-small" onClick={() => setError(null)} type="button">
              Dismiss
            </button>
          </div>
        )}

        {assignment && <AssignmentBrief assignment={assignment} />}

        {step === "write" && (
          <SubmitStep
            busy={busy}
            draft={draft}
            onDraft={setDraft}
            onExample={() => setDraft(EXAMPLE)}
            onSubmit={handIn}
          />
        )}

        {step === "answer" && submission?.probe && (
          <ProbeStep busy={busy} onAnswer={answer} probe={submission.probe} />
        )}

        {step === "marked" && submission?.evaluation && (
          <EvaluationStep evaluation={submission.evaluation} />
        )}
      </div>
    </main>
  );
}
