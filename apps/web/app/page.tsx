"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { api } from "@/lib/api";
import type { Assignment, Subject } from "@/lib/types";

/* Two doors, one per user. Each shows what is actually behind it — subjects and counts
   read from the same endpoints the tools themselves use — so the page is a status board
   rather than a splash screen. A failed call drops its line and leaves the door working. */
export default function HomePage() {
  const [subjects, setSubjects] = useState<Subject[] | null>(null);
  const [assignments, setAssignments] = useState<Assignment[] | null>(null);

  useEffect(() => {
    api
      .subjects()
      .then((body) => setSubjects(body.subjects))
      .catch(() => undefined);
    api
      .assignments()
      .then((body) => setAssignments(body.assignments))
      .catch(() => undefined);
  }, []);

  const topics =
    subjects?.reduce(
      (total, subject) =>
        total + subject.catalog.grades.reduce((sum, grade) => sum + grade.topics.length, 0),
      0,
    ) ?? 0;
  const assignment = assignments?.[0];
  const coreTasks = assignment?.tasks.filter((task) => task.mode === "core").length ?? 0;

  return (
    <div className="shell">
      <AppHeader />

      <main className="doors">
        <Link className="door door-teacher" href="/lessons">
          <span className="u-label">Teacher</span>
          <span className="door-title">Lessons</span>
          <span className="door-facts">
            {subjects && subjects.length > 0 && (
              <span className="u-mono">
                {subjects.map((subject) => subject.label).join(" · ")} · {topics} topics
              </span>
            )}
            <span className="u-mono">video · 3 recap cards</span>
          </span>
          <span className="door-go">
            Make a lesson <span aria-hidden="true">→</span>
          </span>
        </Link>

        <Link className="door door-student" href="/assignments">
          <span className="u-label">Student</span>
          <span className="door-title">Assignments</span>
          <span className="door-facts">
            {assignment && <span className="u-mono">{assignment.title}</span>}
            {coreTasks > 0 && (
              <span className="u-mono">
                {coreTasks} {coreTasks === 1 ? "task is" : "tasks are"} yours
              </span>
            )}
          </span>
          <span className="door-go">
            Open <span aria-hidden="true">→</span>
          </span>
        </Link>
      </main>
    </div>
  );
}
