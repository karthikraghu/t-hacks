"use client";

import { useEffect, useRef, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { AssignmentBrief } from "@/components/AssignmentBrief";
import { EvaluationStep } from "@/components/EvaluationStep";
import { ProbeStep } from "@/components/ProbeStep";
import { StepRail } from "@/components/StepRail";
import { SubmitStep } from "@/components/SubmitStep";
import { api } from "@/lib/api";
import { assignmentSteps } from "@/lib/labels";
import type { Assignment, Marking, Submission } from "@/lib/types";

type Step = "write" | "answer" | "marked";

const stepOrder: Step[] = ["write", "answer", "marked"];

export default function AssignmentsPage() {
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [marking, setMarking] = useState<Marking | null>(null);
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
      .then((body) => {
        setAssignment(body.assignments[0] ?? null);
        setMarking(body.marking);
      })
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

  return (
    <div className="shell">
      <AppHeader>
        <StepRail current={stepOrder.indexOf(step)} steps={assignmentSteps} />
      </AppHeader>

      <main className="main">
        <div className="stack">
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
              example={assignment?.example_response ?? null}
              marking={marking}
              onDraft={setDraft}
              onSubmit={handIn}
            />
          )}

          {step === "answer" && submission && submission.exchanges.length > 0 && (
            <ProbeStep
              busy={busy}
              exchange={submission.exchanges[submission.exchanges.length - 1]}
              index={submission.exchanges.length - 1}
              // Keyed by question so every follow-up remounts the listen-answer cycle.
              key={submission.exchanges.length - 1}
              onAnswer={answer}
              questionLimit={marking?.question_limit ?? submission.exchanges.length}
              submissionId={submission.id}
            />
          )}

          {step === "marked" && submission?.evaluation && (
            <EvaluationStep evaluation={submission.evaluation} />
          )}
        </div>
      </main>
    </div>
  );
}
