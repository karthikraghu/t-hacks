"use client";

import { RefObject } from "react";
import { api } from "@/lib/api";
import { timecode, totalDuration } from "@/lib/format";
import type { RenderJob, Storyboard } from "@/lib/types";

interface Props {
  headingRef: RefObject<HTMLHeadingElement | null>;
  job: RenderJob;
  onStartOver: () => void;
  storyboard: Storyboard | null;
}

export function FilesStep({ headingRef, job, onStartOver, storyboard }: Props) {
  const video = job.artifacts.find((artifact) => artifact.kind === "video");
  const cards = job.artifacts.filter((artifact) => artifact.kind === "card");

  return (
    <div className="stack">
      <div className="page-head">
        <h1 className="u-display" ref={headingRef} tabIndex={-1}>
          {storyboard?.title ?? "Your lesson"}
        </h1>
        <div className="page-head-meta">
          {storyboard && <span className="tag u-mono">{timecode(totalDuration(storyboard.sections))}</span>}
          <button className="btn btn-quiet" onClick={onStartOver} type="button">
            Make another lesson
          </button>
        </div>
      </div>

      {job.provenance === "cached" && (
        <div className="alert alert-info" role="status">
          <p>
            <strong>This is the prepared example, not a live render.</strong> Live generation was unavailable, so
            the stored version of this lesson is shown instead.
          </p>
        </div>
      )}

      {video && (
        <div className="video-frame">
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <video controls preload="metadata" src={api.artifactUrl(video.url)} />
          <div className="video-foot">
            <span className="u-label">{video.name}</span>
            <a className="btn btn-primary btn-small" download href={api.artifactUrl(video.url)}>
              Download MP4
            </a>
          </div>
        </div>
      )}

      {cards.length > 0 && (
        <section>
          <p className="u-label u-spaced-b">Recap cards</p>
          <div className="cards-grid">
            {cards.map((artifact, index) => (
              <figure className="recap" key={artifact.name} style={{ margin: 0 }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img alt={`Recap card ${index + 1}`} src={api.artifactUrl(artifact.url)} />
                <figcaption className="recap-foot">
                  <span className="u-label">Card {index + 1}</span>
                  <a className="link-download" download href={api.artifactUrl(artifact.url)}>
                    Download PNG
                  </a>
                </figcaption>
              </figure>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
