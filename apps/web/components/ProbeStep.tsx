"use client";

import { KeyboardEvent, useState } from "react";
import type { SubmissionProbe } from "@/lib/types";

interface Props {
  busy: boolean;
  onAnswer: (answer: string) => void;
  probe: SubmissionProbe;
}

export function ProbeStep({ busy, onAnswer, probe }: Props) {
  const [draft, setDraft] = useState("");

  function send() {
    const answer = draft.trim();
    if (answer) onAnswer(answer);
  }

  function keys(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      send();
    }
  }

  return (
    <>
      <div className="page-head">
        <p className="u-label">One question</p>
        <h1 className="u-display">About your own reasoning</h1>
      </div>

      <div className="probe-card">
        <p>{probe.question}</p>
        <p className="probe-quote">“{probe.quoted_span}”</p>
      </div>

      <div className="alert alert-info" role="note">
        <p>
          Answer in your own words. There is no right length — say what you were thinking when you
          made that choice.
        </p>
      </div>

      <div className="mark-form">
        <div className="field">
          <label htmlFor="answer">Your answer</label>
          <textarea
            id="answer"
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={keys}
            rows={5}
            value={draft}
          />
        </div>
        <div className="mark-actions">
          <button className="btn btn-primary" disabled={busy} onClick={send} type="button">
            {busy ? "Marking…" : "Send answer"}
          </button>
        </div>
      </div>
    </>
  );
}
