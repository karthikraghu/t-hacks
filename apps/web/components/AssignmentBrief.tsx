"use client";

import { taskModeLabels, taskModes } from "@/lib/labels";
import type { Assignment } from "@/lib/types";

interface Props {
  assignment: Assignment;
}

export function AssignmentBrief({ assignment }: Props) {
  return (
    <section className="card">
      {/* `.card` carries no padding of its own — every direct child is a `.section`,
          exactly as in SetupStep. */}
      <div className="section">
        <h2 className="u-h2">{assignment.title}</h2>
        <p className="u-muted u-spaced">{assignment.brief}</p>
      </div>

      {taskModes.map((mode) => {
        const rows = assignment.tasks.filter((task) => task.mode === mode);
        // A generated assignment can be all-core, leaving a mode with no tasks. Skip the
        // group entirely rather than print a heading over nothing.
        if (rows.length === 0) return null;
        return (
          <div className="section" key={mode}>
            <p className="u-label">{taskModeLabels[mode]}</p>
            <div className="task-split">
              {rows.map((task) => (
                <div
                  className={mode === "core" ? "task-row is-core" : "task-row"}
                  key={task.description}
                >
                  {task.description}
                  <span className="u-note"> {task.rationale}</span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </section>
  );
}
