"use client";

import { sceneNumber, timecode, totalDuration } from "@/lib/format";
import type { StoryboardSection } from "@/lib/types";

interface Props {
  sections: StoryboardSection[];
  activeId?: string | null;
  onSelect?: (sectionId: string) => void;
  working?: boolean;
}

/**
 * One segment per scene, sized by its real duration, over a tick rail drawn from
 * the same number — so one tick is always ten seconds of finished video.
 */
export function LessonRuler({ sections, activeId, onSelect, working = false }: Props) {
  const total = totalDuration(sections);
  if (total <= 0) return null;

  const labelStep = total > 150 ? 60 : 30;
  const labels: number[] = [];
  for (let mark = 0; mark < total; mark += labelStep) labels.push(mark);
  labels.push(total);

  const ticks: number[] = [];
  for (let mark = 10; mark < total; mark += 10) ticks.push(mark);

  return (
    <div className={`ruler${working ? " ruler-working" : ""}`} style={{ ["--secs" as string]: total }}>
      <div className="ruler-track">
        {sections.map((section, index) =>
          onSelect ? (
            <button
              className={`ruler-seg${activeId === section.id ? " is-active" : ""}`}
              key={section.id}
              onClick={() => onSelect(section.id)}
              style={{ flexGrow: section.duration_seconds }}
              title={`${section.title} · ${timecode(section.duration_seconds)}`}
              type="button"
            >
              {sceneNumber(index)}
            </button>
          ) : (
            <span
              className="ruler-seg"
              key={section.id}
              style={{ flexGrow: section.duration_seconds }}
              title={`${section.title} · ${timecode(section.duration_seconds)}`}
            >
              {sceneNumber(index)}
            </span>
          ),
        )}
      </div>
      <div aria-hidden="true" className="ruler-ticks">
        {ticks.map((mark) => (
          <span className="ruler-tick-mark" key={mark} style={{ left: `${(mark / total) * 100}%` }} />
        ))}
      </div>
      <div aria-hidden="true" className="ruler-scale">
        {labels.map((mark, index) => (
          <span
            className={`ruler-tick${index === 0 ? " is-first" : ""}${
              index === labels.length - 1 ? " is-last" : ""
            }`}
            key={mark}
            style={{ left: `${(mark / total) * 100}%` }}
          >
            {timecode(mark)}
          </span>
        ))}
      </div>
      <p className="u-label u-spaced">{sections.length} scenes · one tick = 10 seconds</p>
    </div>
  );
}
