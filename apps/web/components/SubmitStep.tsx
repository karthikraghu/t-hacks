"use client";

import { FormEvent } from "react";

interface Props {
  busy: boolean;
  draft: string;
  onDraft: (value: string) => void;
  onExample: () => void;
  onSubmit: () => void;
}

export function SubmitStep({ busy, draft, onDraft, onExample, onSubmit }: Props) {
  function send(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <form onSubmit={send}>
      <div className="page-head">
        <p className="u-label">Your work</p>
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
          <button className="btn btn-quiet btn-small" onClick={onExample} type="button">
            Use the worked example
          </button>
        </div>
      </div>

      <div className="approve-bar">
        <p className="u-muted">
          After you hand in, you will have a short spoken conversation about your own reasoning —
          up to three questions. It counts towards the mark.
        </p>
        <div className="approve-actions">
          <button className="btn btn-primary" disabled={busy} type="submit">
            {busy ? "Reading your work…" : "Hand in"}
          </button>
        </div>
      </div>
    </form>
  );
}
