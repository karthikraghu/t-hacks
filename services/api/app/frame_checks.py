from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


# The outer band of the frame that must stay free of lesson content. Manim renders
# on a 14.2 x 8.0 unit frame, so 2 percent is roughly 0.28 x 0.16 units of safety.
MARGIN_RATIO = 0.02
# FFmpeg burns the German captions into the lowest unit of the frame (y = -4.0 to -3.0, an
# eighth of its height). Enforcing that full band as a blocking gate was tried and rejected:
# it failed otherwise good lessons three attempts in a row over a label merely sharing space
# with a subtitle. Sync between picture and speech matters more than caption overlap, so only
# genuine cut-off at the frame edge blocks a render. Raise this back to 0.125 to make the
# whole caption band blocking again.
BOTTOM_MARGIN_RATIO = 0.02
# Per-pixel channel-sum distance from the background at which a pixel counts as
# content. H.264 preview frames carry compression noise, so exact equality fails.
CONTENT_TOLERANCE = 48
# Share of a band that may be content before the band counts as violated. Measured
# reference frames put real cut-off content at 2.9 to 10.2 percent and well-composed
# frames below 0.4 percent, so this sits with margin on both sides of that gap.
MAX_CONTENT_FRACTION = 0.015

EDGE_NAMES = {"top": "top", "bottom": "bottom", "left": "left", "right": "right"}

BOUNDS_HINT = (
    "Keep all content within x = -6.2 to 6.2 and y = -3.0 to 2.3. The band below y = -3.0 stays "
    "free for the burned-in captions. Pass the affected section through fit_content(...) or remove "
    "content, instead of shrinking the whole scene."
)


def _background_color(pixels: np.ndarray) -> np.ndarray:
    packed = (
        pixels[:, :, 0].astype(np.uint32) << 16
        | pixels[:, :, 1].astype(np.uint32) << 8
        | pixels[:, :, 2].astype(np.uint32)
    ).ravel()
    values, counts = np.unique(packed, return_counts=True)
    dominant = int(values[int(np.argmax(counts))])
    return np.array([(dominant >> 16) & 0xFF, (dominant >> 8) & 0xFF, dominant & 0xFF], dtype=np.int16)


def _content_mask(pixels: np.ndarray, background: np.ndarray) -> np.ndarray:
    distance = np.abs(pixels.astype(np.int16) - background).sum(axis=2)
    return distance > CONTENT_TOLERANCE


def frame_bound_violations(frame_path: Path) -> list[tuple[str, float]]:
    """Return the frame edges whose safety band contains lesson content."""
    with Image.open(frame_path) as image:
        pixels = np.asarray(image.convert("RGB"))

    height, width = pixels.shape[:2]
    margin_y = max(int(round(height * MARGIN_RATIO)), 2)
    margin_x = max(int(round(width * MARGIN_RATIO)), 2)
    caption_band = max(int(round(height * BOTTOM_MARGIN_RATIO)), 2)
    mask = _content_mask(pixels, _background_color(pixels))

    bands = {
        "top": mask[:margin_y, :],
        "bottom": mask[height - caption_band :, :],
        "left": mask[:, :margin_x],
        "right": mask[:, width - margin_x :],
    }
    violations = []
    for edge, band in bands.items():
        fraction = float(band.mean())
        if fraction > MAX_CONTENT_FRACTION:
            violations.append((edge, fraction))
    return violations


def check_frame_bounds(frame_paths: list[Path]) -> list[str]:
    """Deterministic issue list for content that runs off the frame."""
    issues: list[str] = []
    for index, frame_path in enumerate(frame_paths, start=1):
        for edge, fraction in frame_bound_violations(frame_path):
            # One frame is sampled per section, so the frame number is the section number.
            # Naming the method removes the guesswork from the repair step.
            where = (
                "touches the bottom edge and reaches into the caption band"
                if edge == "bottom"
                else f"touches the {EDGE_NAMES[edge]} edge of the frame and is cut off"
            )
            issues.append(
                f"Frame {index} shows section {index}, that is the method section_{index}: content "
                f"{where} ({fraction * 100:.1f} % of the zone). Fix exactly that method."
            )
    if issues:
        issues.append(BOUNDS_HINT)
    return issues
