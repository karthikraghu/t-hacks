"use client";

import { RefObject } from "react";
import { LessonRuler } from "@/components/LessonRuler";
import { timecode } from "@/lib/format";
import { renderStages } from "@/lib/labels";
import type { RenderJob, Storyboard } from "@/lib/types";

interface Props {
  elapsedSeconds: number;
  headingRef: RefObject<HTMLHeadingElement | null>;
  job: RenderJob;
  onStartOver: () => void;
  storyboard: Storyboard | null;
}

export function RenderStep({ elapsedSeconds, headingRef, job, onStartOver, storyboard }: Props) {
  const failed = job.status === "failed";
  const currentIndex = renderStages.findIndex((stage) => stage.status === job.status);

  return (
    <div className="stack">
      <div className="page-head">
        <h1 className="u-display" ref={headingRef} tabIndex={-1}>
          {failed ? "The render stopped" : "Rendering your lesson"}
        </h1>
        {!failed && <span className="tag u-mono">{timecode(elapsedSeconds)} elapsed</span>}
      </div>

      <div className="card render-card">
        <div className="render-top">
          <div>
            <h2 className="u-h2">{storyboard?.title}</h2>
            {failed && <p className="u-note u-spaced">Nothing was saved, and the script cannot be reopened.</p>}
          </div>
        </div>

        {storyboard && !failed && <LessonRuler sections={storyboard.sections} working />}

        <ol className="stages">
          {renderStages.map((stage, index) => {
            let state = "";
            if (failed && index === Math.max(currentIndex, 0)) state = " is-failed";
            else if (job.status === "ready") state = " is-done";
            else if (currentIndex > index) state = " is-done";
            else if (currentIndex === index) state = " is-live";
            return (
              <li className={`stage${state}`} key={stage.status}>
                <span aria-hidden="true" className="stage-icon" />
                <span>{stage.label}</span>
                <span className="stage-note">{stage.note}</span>
              </li>
            );
          })}
        </ol>

        <p aria-live="polite" className="render-message" role="status">
          {job.message}
          {job.attempt_count > 1 && !failed && ` · attempt ${job.attempt_count}`}
        </p>

        {failed && (
          <button className="btn btn-primary u-spaced" onClick={onStartOver} type="button">
            Start a new lesson
          </button>
        )}
      </div>
    </div>
  );
}
