"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AppHeader } from "@/components/AppHeader";
import { AssignmentBrief } from "@/components/AssignmentBrief";
import { EvaluationStep } from "@/components/EvaluationStep";
import { ProbeStep } from "@/components/ProbeStep";
import { StepRail } from "@/components/StepRail";
import { SubmitStep } from "@/components/SubmitStep";
import { ApiError, api } from "@/lib/api";
import { learnSteps } from "@/lib/labels";
import { useAssignmentFlow } from "@/lib/useAssignmentFlow";
import type { LearningPackage } from "@/lib/types";

/* The video and its recap cards, shown full on the Watch step and again, tucked away,
   as resources while the student works. One place, so the two never disagree. */
function LessonResources({ pkg }: { pkg: LearningPackage }) {
  const video = pkg.artifacts.find((artifact) => artifact.kind === "video");
  const cards = pkg.artifacts.filter((artifact) => artifact.kind === "card");

  return (
    <>
      {video && (
        <div className="video-frame">
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <video controls preload="metadata" src={api.artifactUrl(video.url)} />
        </div>
      )}
      {cards.length > 0 && (
        <section>
          <p className="u-label u-spaced-b">Recap cards</p>
          <div className="cards-grid">
            {cards.map((artifact, index) => (
              <figure className="recap" key={artifact.name} style={{ margin: 0 }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img alt={`Recap card ${index + 1}`} src={api.artifactUrl(artifact.url)} />
              </figure>
            ))}
          </div>
        </section>
      )}
    </>
  );
}

export default function LearnPage() {
  const params = useParams();
  const jobId = typeof params.jobId === "string" ? params.jobId : "";

  const [pkg, setPkg] = useState<LearningPackage | null>(null);
  const [preparing, setPreparing] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  // The video sits before the assignment, so watching is a fourth step the shared flow
  // does not know about. It is a plain gate the student clears once.
  const [watched, setWatched] = useState(false);

  const flow = useAssignmentFlow(pkg?.assignment ?? null);
  const { submission, step, busy } = flow;

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    let timer: number | undefined;

    async function load() {
      try {
        const body = await api.learningPackage(jobId);
        if (cancelled) return;
        setPkg(body);
        setPreparing(false);
        setLoadError(null);
        // Loaded: stop polling, so a watched lesson never re-fetches under the student.
        if (timer) window.clearInterval(timer);
      } catch (reason) {
        if (cancelled) return;
        // 409 is the lesson still rendering: keep polling and show "come back shortly".
        if (reason instanceof ApiError && reason.status === 409) {
          setPreparing(true);
        } else {
          setLoadError(reason instanceof Error ? reason.message : "This package could not be loaded.");
          if (timer) window.clearInterval(timer);
        }
      }
    }

    load();
    timer = window.setInterval(load, 4000);
    return () => {
      cancelled = true;
      if (timer) window.clearInterval(timer);
    };
  }, [jobId]);

  // Watch is step 0; after that the shared flow's three steps map straight onto Work,
  // Questions and Mark.
  const railIndex = !watched ? 0 : step === "write" ? 1 : step === "answer" ? 2 : 3;
  const error = flow.error ?? loadError;

  return (
    <div className="shell">
      <AppHeader>
        <StepRail current={railIndex} steps={learnSteps} />
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

          {!pkg && preparing && (
            <div className="page-head">
              <p className="u-label">Almost ready</p>
              <h1 className="u-display">Your teacher is still preparing this lesson</h1>
              <p className="u-muted u-spaced">
                The video is being made now. This page will open on its own the moment it is ready —
                come back shortly.
              </p>
            </div>
          )}

          {!pkg && !preparing && !loadError && (
            <div className="page-head">
              <h1 className="u-display">Loading the lesson…</h1>
            </div>
          )}

          {pkg && (
            <>
              {/* Watch */}
              {!watched && (
                <>
                  <div className="page-head">
                    <p className="u-label">Watch</p>
                    <h1 className="u-display">{pkg.title}</h1>
                    <p className="u-muted u-spaced">{pkg.learning_objective}</p>
                  </div>

                  <LessonResources pkg={pkg} />

                  <div className="alert alert-info" role="note">
                    <p>
                      <strong>The assignment is part of this lesson, not optional.</strong> The
                      lesson is not finished when the video ends — to complete it you must do the
                      part that is yours and answer spoken questions about your own reasoning.
                    </p>
                  </div>

                  <div className="approve-bar">
                    <div className="approve-actions">
                      <button className="btn btn-primary" onClick={() => setWatched(true)} type="button">
                        I’ve watched this — start the assignment
                      </button>
                    </div>
                  </div>
                </>
              )}

              {/* Work */}
              {watched && step === "write" && (
                <>
                  <AssignmentBrief assignment={pkg.assignment} />
                  <SubmitStep
                    busy={busy}
                    draft={flow.draft}
                    example={pkg.assignment.example_response ?? null}
                    marking={pkg.marking}
                    onDraft={flow.setDraft}
                    onSubmit={flow.handIn}
                  />
                  <details className="resources">
                    <summary>Lesson resources</summary>
                    <div className="stack u-spaced">
                      <LessonResources pkg={pkg} />
                    </div>
                  </details>
                </>
              )}

              {/* Questions */}
              {watched && step === "answer" && submission && submission.exchanges.length > 0 && (
                <ProbeStep
                  busy={busy}
                  exchange={submission.exchanges[submission.exchanges.length - 1]}
                  index={submission.exchanges.length - 1}
                  // Keyed by question so every follow-up remounts the listen-answer cycle.
                  key={submission.exchanges.length - 1}
                  onAnswer={flow.answer}
                  questionLimit={pkg.marking.question_limit}
                  submissionId={submission.id}
                />
              )}

              {/* Mark */}
              {watched && step === "marked" && submission?.evaluation && (
                <EvaluationStep evaluation={submission.evaluation} submissionId={submission.id} />
              )}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
