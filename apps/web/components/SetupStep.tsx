"use client";

import { FormEvent, RefObject } from "react";
import { levelLabels, levels, methodLabels, methods } from "@/lib/labels";
import type { Catalog, LessonRequest, Level, Method, Subject } from "@/lib/types";

interface Props {
  busy: boolean;
  catalog: Catalog;
  headingRef: RefObject<HTMLHeadingElement | null>;
  lesson: LessonRequest;
  onGrade: (grade: number) => void;
  onLevel: (level: Level) => void;
  onMethod: (method: Method) => void;
  onObjective: (objective: string) => void;
  onSubject: (subjectId: string) => void;
  onSubmit: () => void;
  onSubtopic: (subtopicId: string) => void;
  onTopic: (topicId: string) => void;
  subjects: Subject[];
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
  onSubject,
  onSubmit,
  onSubtopic,
  onTopic,
  subjects,
}: Props) {
  const grade = catalog.grades.find((entry) => entry.grade === lesson.grade);
  const topic = grade?.topics.find((entry) => entry.id === lesson.topic_id);
  const subtopic = topic?.subtopics.find((entry) => entry.id === lesson.subtopic_id);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit();
  }

  return (
    <form onSubmit={submit}>
      <div className="page-head">
        <h1 className="u-display" ref={headingRef} tabIndex={-1}>
          What should the video teach?
        </h1>
      </div>

      <div className="card">
        {/* With a single installed pack the choice does not exist, so neither does the row. */}
        {subjects.length > 1 && (
          <fieldset className="section section-set">
            <legend className="u-label">Subject</legend>
            <div className="choice-row">
              {subjects.map((entry) => (
                <label className="choice" key={entry.id}>
                  <input
                    checked={entry.id === lesson.subject_id}
                    name="subject"
                    onChange={() => onSubject(entry.id)}
                    type="radio"
                  />
                  <span className="choice-pill">{entry.label}</span>
                </label>
              ))}
            </div>
          </fieldset>
        )}

        <fieldset className="section section-set">
          <legend className="u-label">Grade</legend>
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
        </div>

        <div className="setup-foot">
          <p className="u-note u-narrow">{catalog.notice}</p>
          <button className="btn btn-primary" disabled={busy} type="submit">
            {busy ? "Writing the script…" : "Write the script"}
          </button>
        </div>
      </div>
    </form>
  );
}

/** Stands in until the catalogue arrives — the form has nothing to choose from before it. */
export function SetupSkeleton() {
  return (
    <div className="card">
      <div className="section">
        <p className="u-label u-spaced-b">Grade</p>
        <div className="skeleton-row">
          {[0, 1, 2, 3, 4, 5].map((key) => (
            <span className="skeleton" key={key} />
          ))}
        </div>
      </div>
      <div className="section">
        <p className="u-label u-spaced-b">Topic</p>
        <div className="skeleton-row">
          {[0, 1].map((key) => (
            <span className="skeleton skeleton-wide" key={key} />
          ))}
        </div>
      </div>
    </div>
  );
}
