"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AppHeader } from "@/components/AppHeader";
import { FilesStep } from "@/components/FilesStep";
import { RenderStep } from "@/components/RenderStep";
import { ScriptStep } from "@/components/ScriptStep";
import { SetupSkeleton, SetupStep } from "@/components/SetupStep";
import { StepRail } from "@/components/StepRail";
import { api } from "@/lib/api";
import { activeStatuses, lessonSteps } from "@/lib/labels";
import type {
  LessonRequest,
  Level,
  Method,
  RenderJob,
  Storyboard,
  StoryboardSection,
  Subject,
  Subtopic,
} from "@/lib/types";

type Step = "setup" | "script" | "render" | "files";

const stepOrder: Step[] = ["setup", "script", "render", "files"];

function fromSubtopic(subtopic: Subtopic) {
  return {
    subtopic_id: subtopic.id,
    objective: subtopic.learning_goal ?? "",
    method: subtopic.default_method ?? "auto",
  } satisfies Partial<LessonRequest>;
}

/** The subject's hero subtopic if its catalogue marks one, otherwise its first entry. */
function openingSelection(subject: Subject): LessonRequest | null {
  for (const grade of subject.catalog.grades) {
    for (const topic of grade.topics) {
      const hero = topic.subtopics.find((entry) => entry.hero);
      if (hero) {
        return {
          subject_id: subject.id,
          grade: grade.grade,
          topic_id: topic.id,
          level: "standard",
          ...fromSubtopic(hero),
        };
      }
    }
  }
  const grade = subject.catalog.grades[0];
  const topic = grade?.topics[0];
  const subtopic = topic?.subtopics[0];
  if (!grade || !topic || !subtopic) return null;
  return {
    subject_id: subject.id,
    grade: grade.grade,
    topic_id: topic.id,
    level: "standard",
    ...fromSubtopic(subtopic),
  };
}

export default function LessonsPage() {
  const [subjects, setSubjects] = useState<Subject[] | null>(null);
  const [step, setStep] = useState<Step>("setup");
  // Held empty until the catalogues arrive, so no grade or topic id is written twice.
  const [lesson, setLesson] = useState<LessonRequest | null>(null);
  const [storyboard, setStoryboard] = useState<Storyboard | null>(null);
  const [job, setJob] = useState<RenderJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [revisingId, setRevisingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const headingRef = useRef<HTMLHeadingElement | null>(null);
  const startedAt = useRef<number>(0);

  // The catalogue chooses what opens: the first subject's hero subtopic, or its first
  // entry. Nothing here names a subject, grade or id, so the two cannot drift apart.
  useEffect(() => {
    api
      .subjects()
      .then((loaded) => {
        setSubjects(loaded.subjects);
        const first = loaded.subjects[0];
        const opening = first ? openingSelection(first) : null;
        if (opening) setLesson(opening);
      })
      .catch((reason: Error) => setError(reason.message));
  }, []);

  // Everything below reads the active subject's catalogue through this one lookup.
  const catalog = subjects?.find((entry) => entry.id === lesson?.subject_id)?.catalog ?? null;

  // Poll only while the job is genuinely in flight; the status is the only trigger.
  const jobId = job?.id;
  const jobStatus = job?.status;
  useEffect(() => {
    if (!jobId || !jobStatus || !activeStatuses.includes(jobStatus)) return;
    const timer = window.setInterval(async () => {
      try {
        const current = await api.job(jobId);
        setJob(current);
        if (current.status === "ready" || current.status === "cached_fallback") setStep("files");
        if (current.status === "failed") setError(null);
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "The render status could not be read.");
      }
    }, 1800);
    return () => window.clearInterval(timer);
  }, [jobId, jobStatus]);

  useEffect(() => {
    if (step !== "render") return;
    const timer = window.setInterval(() => {
      setElapsed(Math.round((Date.now() - startedAt.current) / 1000));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [step]);

  // Send focus to the heading of the step the teacher just moved to. Comparing the
  // previous value rather than a mount flag keeps the effect safe under the double
  // invocation React does in development, which would otherwise focus on first paint.
  const lastStep = useRef<Step>(step);
  useEffect(() => {
    if (lastStep.current === step) return;
    lastStep.current = step;
    headingRef.current?.focus();
  }, [step]);

  const selectSubject = useCallback(
    (subjectId: string) => {
      const subject = subjects?.find((candidate) => candidate.id === subjectId);
      if (!subject) return;
      const opening = openingSelection(subject);
      if (opening) setLesson(opening);
    },
    [subjects],
  );

  const selectGrade = useCallback(
    (grade: number) => {
      const entry = catalog?.grades.find((candidate) => candidate.grade === grade);
      const topic = entry?.topics[0];
      const subtopic = topic?.subtopics[0];
      if (!topic || !subtopic) return;
      setLesson((current) =>
        current ? { ...current, grade, topic_id: topic.id, ...fromSubtopic(subtopic) } : current,
      );
    },
    [catalog],
  );

  const selectTopic = useCallback(
    (topicId: string) => {
      const grade = catalog?.grades.find((candidate) => candidate.grade === lesson?.grade);
      const topic = grade?.topics.find((candidate) => candidate.id === topicId);
      const subtopic = topic?.subtopics[0];
      if (!subtopic) return;
      setLesson((current) =>
        current ? { ...current, topic_id: topicId, ...fromSubtopic(subtopic) } : current,
      );
    },
    [catalog, lesson?.grade],
  );

  const selectSubtopic = useCallback(
    (subtopicId: string) => {
      const grade = catalog?.grades.find((candidate) => candidate.grade === lesson?.grade);
      const topic = grade?.topics.find((candidate) => candidate.id === lesson?.topic_id);
      const subtopic = topic?.subtopics.find((candidate) => candidate.id === subtopicId);
      if (!subtopic) return;
      setLesson((current) => (current ? { ...current, ...fromSubtopic(subtopic) } : current));
    },
    [catalog, lesson?.grade, lesson?.topic_id],
  );

  async function writeScript() {
    if (!lesson) return;
    setBusy(true);
    setError(null);
    try {
      const draft = await api.createStoryboard({
        ...lesson,
        objective: lesson.objective?.trim() || undefined,
      });
      setStoryboard(draft);
      setStep("script");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The script could not be written.");
    } finally {
      setBusy(false);
    }
  }

  async function revise(section: StoryboardSection, comment: string): Promise<boolean> {
    if (!storyboard) return false;
    setRevisingId(section.id);
    setError(null);
    try {
      setStoryboard(await api.reviseSection(storyboard.id, section.id, comment));
      return true;
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The scene could not be rewritten.");
      return false;
    } finally {
      setRevisingId(null);
    }
  }

  async function approve() {
    if (!storyboard) return;
    setBusy(true);
    setError(null);
    try {
      const nextJob = await api.approve(storyboard.id);
      setJob(nextJob);
      // A prepared (hero) lesson comes back already rendered, so skip the render step
      // and its polling and go straight to the finished files.
      if (nextJob.status === "ready" || nextJob.status === "cached_fallback") {
        setStep("files");
      } else {
        startedAt.current = Date.now();
        setElapsed(0);
        setStep("render");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The render could not be started.");
    } finally {
      setBusy(false);
    }
  }

  function startOver() {
    setStoryboard(null);
    setJob(null);
    setError(null);
    setStep("setup");
  }

  return (
    <div className="shell">
      <AppHeader>
        <StepRail current={stepOrder.indexOf(step)} steps={lessonSteps} />
      </AppHeader>

      <main className="main" id="top">
        {error && (
          <div className="alert alert-error" role="alert">
            <p>{error}</p>
            <button className="btn btn-plain btn-small" onClick={() => setError(null)} type="button">
              Dismiss
            </button>
          </div>
        )}

        {step === "setup" &&
          (catalog && lesson ? (
            <SetupStep
              busy={busy}
              catalog={catalog}
              headingRef={headingRef}
              lesson={lesson}
              onGrade={selectGrade}
              onLevel={(level: Level) => setLesson((current) => (current ? { ...current, level } : current))}
              onMethod={(method: Method) =>
                setLesson((current) => (current ? { ...current, method } : current))
              }
              onObjective={(objective) =>
                setLesson((current) => (current ? { ...current, objective } : current))
              }
              onSubject={selectSubject}
              onSubmit={writeScript}
              onSubtopic={selectSubtopic}
              onTopic={selectTopic}
              subjects={subjects ?? []}
            />
          ) : (
            <SetupSkeleton />
          ))}

        {step === "script" && storyboard && (
          <ScriptStep
            busy={busy}
            headingRef={headingRef}
            onApprove={approve}
            onBack={() => setStep("setup")}
            onRevise={revise}
            revisingId={revisingId}
            storyboard={storyboard}
          />
        )}

        {step === "render" && job && (
          <RenderStep
            elapsedSeconds={elapsed}
            headingRef={headingRef}
            job={job}
            onStartOver={startOver}
            storyboard={storyboard}
          />
        )}

        {step === "files" && job && (
          <FilesStep headingRef={headingRef} job={job} onStartOver={startOver} storyboard={storyboard} />
        )}
      </main>
    </div>
  );
}
