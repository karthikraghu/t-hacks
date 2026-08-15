"use client";

import { FormEvent } from "react";
import type { Marking } from "@/lib/types";

interface Props {
  busy: boolean;
  draft: string;
  /** Present only on the seeded worked example; it fills the box for a demo. */
  example: string | null;
  marking: Marking | null;
  onDraft: (value: string) => void;
  onSubmit: () => void;
}

export function SubmitStep({ busy, draft, example, marking, onDraft, onSubmit }: Props) {
  function send(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <form onSubmit={send}>
      <div className="page-head">
        <h1 className="u-display">Hand in the part that is yours</h1>
      </div>

      <div className="card">
        <div className="section">
          <div className="field">
            <label htmlFor="core">Your reasoning</label>
            <textarea
              id="core"
              onChange={(event) => onDraft(event.target.value)}
              placeholder="Explain the choice you made and why you made it."
              rows={10}
              value={draft}
            />
          </div>
          {example && (
            <button
              className="btn btn-quiet btn-small u-spaced"
              onClick={() => onDraft(example)}
              type="button"
            >
              Fill in the worked example
            </button>
          )}
        </div>
      </div>

      <div className="approve-bar">
        {marking && (
          <p className="u-note">
            <span className="u-mono">{marking.question_limit}</span> spoken questions follow, worth{" "}
            <span className="u-mono">{Math.round(marking.probe_weight * 100)}%</span> of the mark.
          </p>
        )}
        <div className="approve-actions">
          <button className="btn btn-primary" disabled={busy} type="submit">
            {busy ? "Reading your work…" : "Hand in"}
          </button>
        </div>
      </div>
    </form>
  );
}
