"use client";

import type { SubmissionEvaluation } from "@/lib/types";

interface Props {
  evaluation: SubmissionEvaluation;
}

export function EvaluationStep({ evaluation }: Props) {
  return (
    <>
      <div className="page-head">
        <p className="u-label">Marked</p>
        <h1 className="u-display">{evaluation.weighted_score}</h1>
      </div>

      <div className="card">
        <div className="section">
          {/* Both parts shown, never just the total: the point of the feature is that
              the written work and the spoken answer are two different measurements. */}
          <div className="score-row">
            <p>
              <span className="u-label">Written work</span>{" "}
              <span className="u-mono">{evaluation.core_score}</span>
            </p>
            <p>
              <span className="u-label">Your answer</span>{" "}
              <span className="u-mono">{evaluation.probe_score}</span>
            </p>
            <p>
              <span className="u-label">Answer counts for</span>{" "}
              <span className="u-mono">{Math.round(evaluation.probe_weight * 100)}%</span>
            </p>
          </div>

          <p>{evaluation.comment}</p>
        </div>

        <div className="section">
          <p className="u-label">What worked</p>
          <ul>
            {evaluation.strengths.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>

        <div className="section">
          <p className="u-label">What to change</p>
          <ul>
            {evaluation.gaps.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
}
