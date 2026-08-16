"use client";

import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { AssignmentBrief } from "@/components/AssignmentBrief";
import { EvaluationStep } from "@/components/EvaluationStep";
import { ProbeStep } from "@/components/ProbeStep";
import { StepRail } from "@/components/StepRail";
import { SubmitStep } from "@/components/SubmitStep";
import { api } from "@/lib/api";
import { assignmentSteps } from "@/lib/labels";
import { useAssignmentFlow, type AssignmentStep } from "@/lib/useAssignmentFlow";
import type { Assignment, Marking } from "@/lib/types";

const stepOrder: AssignmentStep[] = ["write", "answer", "marked"];

export default function AssignmentsPage() {
  const [assignment, setAssignment] = useState<Assignment | null>(null);
  const [marking, setMarking] = useState<Marking | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const flow = useAssignmentFlow(assignment);
  const { submission, step, busy } = flow;

  useEffect(() => {
    api
      .assignments()
      .then((body) => {
        setAssignment(body.assignments[0] ?? null);
        setMarking(body.marking);
      })
      .catch((reason) =>
        setLoadError(reason instanceof Error ? reason.message : "The assignments could not be loaded."),
      );
  }, []);

  const error = flow.error ?? loadError;

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
              <button
                className="btn btn-plain btn-small"
                onClick={() => {
                  flow.dismissError();
                  setLoadError(null);
                }}
                type="button"
              >
                Dismiss
              </button>
            </div>
          )}

          {assignment && <AssignmentBrief assignment={assignment} />}

          {step === "write" && (
            <SubmitStep
              busy={busy}
              draft={flow.draft}
              example={assignment?.example_response ?? null}
              marking={marking}
              onDraft={flow.setDraft}
              onSubmit={flow.handIn}
            />
          )}

          {step === "answer" && submission && submission.exchanges.length > 0 && (
            <ProbeStep
              busy={busy}
              exchange={submission.exchanges[submission.exchanges.length - 1]}
              index={submission.exchanges.length - 1}
              // Keyed by question so every follow-up remounts the listen-answer cycle.
              key={submission.exchanges.length - 1}
              onAnswer={flow.answer}
              questionLimit={marking?.question_limit ?? submission.exchanges.length}
              submissionId={submission.id}
            />
          )}

          {step === "marked" && submission?.evaluation && (
            <EvaluationStep evaluation={submission.evaluation} submissionId={submission.id} />
          )}
        </div>
      </main>
    </div>
  );
}
