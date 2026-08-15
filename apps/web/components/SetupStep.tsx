"use client";

import { FormEvent, RefObject } from "react";
import { levelLabels, levels, methodLabels, methods } from "@/lib/labels";
import type { Catalog, LessonRequest, Level, Method } from "@/lib/types";

interface Props {
  busy: boolean;
  catalog: Catalog | null;
  headingRef: RefObject<HTMLHeadingElement | null>;
  lesson: LessonRequest;
  onGrade: (grade: number) => void;
  onLevel: (level: Level) => void;
  onMethod: (method: Method) => void;
  onObjective: (objective: string) => void;
  onSubmit: () => void;
  onSubtopic: (subtopicId: string) => void;
  onTopic: (topicId: string) => void;
}

export function SetupStep({
  busy,
  catalog,
  headingRef,
  lesson,
  onGrade,
  onLevel,
  onMethod,
  onObjective,
  onSubmit,
  onSubtopic,
  onTopic,
}: Props) {
  const grade = catalog?.grades.find((entry) => entry.grade === lesson.grade);
  const topic = grade?.topics.find((entry) => entry.id === lesson.topic_id);
  const subtopic = topic?.subtopics.find((entry) => entry.id === lesson.subtopic_id);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <form onSubmit={submit}>
      <div className="page-head">
        <div>
          <p className="u-label">Step 1</p>
          <h1 className="u-display" ref={headingRef} tabIndex={-1}>
            Set up the lesson
          </h1>
        </div>
        {subtopic?.hero && (
          <span
            className="tag tag-marker"
            title="If live generation is unavailable, a prepared version of this lesson is shown instead."
          >
            Prepared example on file
          </span>
        )}
      </div>

      <div className="card">
        <fieldset className="section section-set">
          <legend className="u-label">Grade</legend>
          {catalog ? (
            <div className="choice-row">
              {catalog.grades.map((entry) => (
                <label className="choice" key={entry.grade}>
                  <input
                    checked={entry.grade === lesson.grade}
                    name="grade"
                    onChange={() => onGrade(entry.grade)}
                    type="radio"
                  />
                  <span className="choice-pill u-mono">{entry.grade}</span>
                </label>
              ))}
            </div>
          ) : (
            <div className="skeleton-row">
              {[0, 1, 2, 3, 4, 5].map((key) => (
                <span className="skeleton" key={key} />
              ))}
            </div>
          )}
        </fieldset>

        <fieldset className="section section-set">
          <legend className="u-label">Topic</legend>
          <div className="choice-grid">
            {grade?.topics.map((entry) => (
              <label className="choice" key={entry.id}>
                <input
                  checked={entry.id === lesson.topic_id}
                  name="topic"
                  onChange={() => onTopic(entry.id)}
                  type="radio"
                />
                <span className="choice-pill choice-pill-block">{entry.label}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="section section-set">
          <legend className="u-label">Focus of the video</legend>
          <div className="choice-grid-3">
            {topic?.subtopics.map((entry) => (
              <label className="choice" key={entry.id}>
                <input
                  checked={entry.id === lesson.subtopic_id}
                  name="subtopic"
                  onChange={() => onSubtopic(entry.id)}
                  type="radio"
                />
                <span className="choice-box">
                  <span className="choice-box-title">{entry.label}</span>
                  {entry.learning_goal && <span className="choice-box-goal">{entry.learning_goal}</span>}
                  {entry.misconceptions && entry.misconceptions.length > 0 && (
                    <span className="choice-box-slips">
                      <span className="u-label">Slips it targets</span>
                      {entry.misconceptions.map((item) => (
                        <span className="slip" key={item}>
                          {item}
                        </span>
                      ))}
                    </span>
                  )}
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="section section-set">
          <legend className="u-label">Pace</legend>
          <div className="choice-row">
            {levels.map((value) => (
              <label className="choice" key={value}>
                <input
                  checked={value === lesson.level}
                  name="level"
                  onChange={() => onLevel(value)}
                  type="radio"
                />
                <span className="choice-pill">{levelLabels[value]}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="section section-set">
          <legend className="u-label">Teaching method</legend>
          <div className="choice-row">
            {methods.map((value) => (
              <label className="choice" key={value}>
                <input
                  checked={value === lesson.method}
                  name="method"
                  onChange={() => onMethod(value)}
                  type="radio"
                />
                <span className="choice-pill">{methodLabels[value]}</span>
              </label>
            ))}
          </div>
          <p className="u-note u-spaced">Choose for me picks the methods that fit this focus and pace.</p>
        </fieldset>

        <div className="section">
          <label className="field">
            <span className="u-label">Learning goal</span>
            <textarea
              onChange={(event) => onObjective(event.target.value)}
              placeholder="What should students be able to do after the video?"
              rows={3}
              value={lesson.objective ?? ""}
            />
          </label>
          <p className="u-note u-spaced">Filled in from the catalogue. Edit it to change the emphasis.</p>
        </div>

        <div className="setup-foot">
          <p className="u-note u-narrow">{catalog?.notice}</p>
          <button className="btn btn-primary" disabled={busy || !catalog} type="submit">
            {busy ? "Writing the script…" : "Write the script"}
          </button>
        </div>
      </div>
    </form>
  );
}
