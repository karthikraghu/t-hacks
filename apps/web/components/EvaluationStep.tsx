"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { SubmissionEvaluation } from "@/lib/types";

interface Props {
  evaluation: SubmissionEvaluation;
  submissionId: string;
}

export function EvaluationStep({ evaluation, submissionId }: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // Autoplay after the answer is often allowed, but the wait for marking can consume the
  // user gesture, so a blocked read falls back to a button — the same pattern as the
  // spoken questions.
  const [needsPlay, setNeedsPlay] = useState(false);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.play().catch(() => setNeedsPlay(true));
    return () => audio.pause();
  }, []);

  function playAgain() {
    audioRef.current
      ?.play()
      .then(() => setNeedsPlay(false))
      .catch(() => undefined);
  }

  return (
    <>
      <div className="page-head">
        <p className="u-label">Marked</p>
        <h1 className="u-display">{evaluation.weighted_score}</h1>
        <button className="btn btn-quiet btn-small u-spaced" onClick={playAgain} type="button">
          {needsPlay ? "Hear your result" : "Play again"}
        </button>
      </div>

      {/* preload so the spoken result is ready the moment the mark appears */}
      <audio preload="auto" ref={audioRef} src={api.evaluationAudioUrl(submissionId)} />

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
              <span className="u-label">Your answers</span>{" "}
              <span className="u-mono">{evaluation.probe_score}</span>
            </p>
            <p>
              <span className="u-label">Answers count for</span>{" "}
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
