"use client";

import { KeyboardEvent, RefObject, useState } from "react";
import { LessonRuler } from "@/components/LessonRuler";
import { cumulativeStarts, sceneNumber, timecode, totalDuration } from "@/lib/format";
import { methodLabels } from "@/lib/labels";
import type { Storyboard, StoryboardSection } from "@/lib/types";

interface Props {
  busy: boolean;
  headingRef: RefObject<HTMLHeadingElement | null>;
  onApprove: () => void;
  onBack: () => void;
  onRevise: (section: StoryboardSection, comment: string) => Promise<boolean>;
  revisingId: string | null;
  storyboard: Storyboard;
}

export function ScriptStep({
  busy,
  headingRef,
  onApprove,
  onBack,
  onRevise,
  revisingId,
  storyboard,
}: Props) {
  const [openId, setOpenId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [activeId, setActiveId] = useState<string | null>(storyboard.sections[0]?.id ?? null);

  const starts = cumulativeStarts(storyboard.sections);
  const total = totalDuration(storyboard.sections);

  function jumpTo(sectionId: string) {
    setActiveId(sectionId);
    document.getElementById(`scene-${sectionId}`)?.scrollIntoView({ block: "center" });
  }

  function openMark(sectionId: string) {
    setOpenId(sectionId);
    setDraft("");
  }

  async function submitMark(section: StoryboardSection) {
    const comment = draft.trim();
    if (!comment) return;
    const applied = await onRevise(section, comment);
    if (applied) {
      setOpenId(null);
      setDraft("");
    }
  }

  function markKeys(event: KeyboardEvent<HTMLTextAreaElement>, section: StoryboardSection) {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
      event.preventDefault();
      void submitMark(section);
    }
    if (event.key === "Escape") setOpenId(null);
  }

  return (
    <div className="stack">
      <div className="page-head">
        <div>
          <p className="u-label">Step 2</p>
          <h1 className="u-display" ref={headingRef} tabIndex={-1}>
            Read the script
          </h1>
        </div>
        <div className="page-head-meta">
          <span className="tag u-mono">{storyboard.sections.length} scenes</span>
          <span className="tag tag-pen u-mono">{timecode(total)}</span>
          {!storyboard.generated_live && <span className="tag tag-marker">Prepared example</span>}
        </div>
      </div>

      <div className="card script-head">
        <div className="script-head-top">
          <div>
            <h2 className="u-h2">{storyboard.title}</h2>
            <p className="script-objective">{storyboard.learning_objective}</p>
          </div>
          <div className="chips">
            {storyboard.selected_methods.map((method) => (
              <span className="tag" key={method}>
                {methodLabels[method]}
              </span>
            ))}
          </div>
        </div>
        <div className="script-ruler">
          <LessonRuler activeId={activeId} onSelect={jumpTo} sections={storyboard.sections} />
        </div>
      </div>

      <div className="scenes">
        {storyboard.sections.map((section, index) => {
          const isOpen = openId === section.id;
          const isRevising = revisingId === section.id;
          return (
            <article
              className={`scene${activeId === section.id ? " is-active" : ""}`}
              id={`scene-${section.id}`}
              key={section.id}
              onFocus={() => setActiveId(section.id)}
            >
              <div className="scene-gutter">
                <span className="scene-index">{sceneNumber(index)}</span>
                <span className="scene-start">{timecode(starts[index])}</span>
              </div>
              <div className="scene-body">
                <div className="scene-title-row">
                  <div>
                    <h3 className="u-h3">{section.title}</h3>
                    {/* The model returns anything from a two-word label to a full sentence here. */}
                    <p className="scene-purpose">{section.purpose}</p>
                  </div>
                  <span className="tag u-mono">{timecode(section.duration_seconds)}</span>
                </div>

                <p className="scene-narration">{section.narration}</p>

                <div className="scene-detail">
                  <div className="scene-detail-row">
                    <span className="u-label">On screen</span>
                    <p>{section.visual_plan}</p>
                  </div>
                  {section.on_screen_text.length > 0 && (
                    <div className="scene-detail-row">
                      <span className="u-label">Labels</span>
                      <span className="chips">
                        {section.on_screen_text.map((item) => (
                          <span className="chip-text" key={item}>
                            {item}
                          </span>
                        ))}
                      </span>
                    </div>
                  )}
                  {section.latex.length > 0 && (
                    <div className="scene-detail-row">
                      <span className="u-label">LaTeX</span>
                      <span className="chips">
                        {section.latex.map((item) => (
                          <code className="chip-code" key={item}>
                            {item}
                          </code>
                        ))}
                      </span>
                    </div>
                  )}
                  {section.check_prompt && (
                    <div className="scene-detail-row">
                      <span className="u-label">Question</span>
                      <p>{section.check_prompt}</p>
                    </div>
                  )}
                </div>

                <div className="scene-foot">
                  {isOpen ? (
                    <div className="mark-form">
                      <label className="field">
                        <span className="u-label">Your note to the writer</span>
                        <textarea
                          autoFocus
                          onChange={(event) => setDraft(event.target.value)}
                          onKeyDown={(event) => markKeys(event, section)}
                          placeholder="Use a ramp instead of a staircase, and slow the last line down."
                          rows={2}
                          value={draft}
                        />
                      </label>
                      <div className="mark-actions">
                        <button
                          className="btn btn-mark"
                          disabled={isRevising || !draft.trim()}
                          onClick={() => void submitMark(section)}
                          type="button"
                        >
                          {isRevising ? "Rewriting…" : "Rewrite this scene"}
                        </button>
                        <button
                          className="btn btn-plain btn-small"
                          disabled={isRevising}
                          onClick={() => setOpenId(null)}
                          type="button"
                        >
                          Cancel
                        </button>
                        <span className="u-label">⌘↵ to send</span>
                      </div>
                    </div>
                  ) : (
                    <button
                      className="btn btn-quiet btn-small"
                      disabled={busy}
                      onClick={() => openMark(section.id)}
                      type="button"
                    >
                      Change this scene
                    </button>
                  )}
                </div>
              </div>
            </article>
          );
        })}
      </div>

      <RecapPreview storyboard={storyboard} />

      <div className="approve-bar">
        <p className="u-note">Approving starts the narration and the render. The script is fixed from then on.</p>
        <div className="approve-actions">
          <button className="btn btn-quiet" disabled={busy} onClick={onBack} type="button">
            Change the setup
          </button>
          <button className="btn btn-primary" disabled={busy} onClick={onApprove} type="button">
            {busy ? "Starting…" : "Approve and render"}
          </button>
        </div>
      </div>
    </div>
  );
}

function RecapPreview({ storyboard }: { storyboard: Storyboard }) {
  if (storyboard.recap_cards.length === 0) return null;
  return (
    <section>
      <p className="u-label u-spaced-b">Recap cards planned from this script</p>
      <div className="cards-grid">
        {storyboard.recap_cards.map((card) => (
          <div className="recap-plan" key={card.title}>
            <h3 className="u-h3">{card.title}</h3>
            <p>{card.message}</p>
            {card.latex.length > 0 && (
              <div className="chips u-spaced">
                {card.latex.map((item) => (
                  <code className="chip-code" key={item}>
                    {item}
                  </code>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
