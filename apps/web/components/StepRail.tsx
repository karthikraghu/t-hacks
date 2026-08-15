"use client";

import { Fragment } from "react";

interface Props {
  current: number;
  steps: readonly string[];
}

export function StepRail({ current, steps }: Props) {
  return (
    <nav aria-label="Progress" className="rail">
      {steps.map((label, index) => {
        const state = index < current ? "is-done" : index === current ? "is-current" : "";
        return (
          <Fragment key={label}>
            {index > 0 && <span aria-hidden="true" className="rail-sep" />}
            <span aria-current={index === current ? "step" : undefined} className={`rail-step ${state}`}>
              <span className="rail-dot">{index < current ? "✓" : index + 1}</span>
              <span>{label}</span>
            </span>
          </Fragment>
        );
      })}
    </nav>
  );
}
