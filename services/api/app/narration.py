from __future__ import annotations

import base64
import re
from dataclasses import dataclass

import httpx

from .models import StoryboardSection
from .settings import Settings


class NarrationFailure(RuntimeError):
    pass


@dataclass
class NarrationPackage:
    audio: bytes
    text: str
    section_durations: list[float]
    srt: str


class ElevenLabsNarration:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create(self, sections: list[StoryboardSection]) -> NarrationPackage:
        if not self.settings.elevenlabs_is_configured:
            raise NarrationFailure("The ElevenLabs API key and voice ID must be configured.")

        text, spans = self._joined_text(sections)
        url = (
            "https://api.elevenlabs.io/v1/text-to-speech/"
            f"{self.settings.elevenlabs_voice_id}/with-timestamps"
        )
        try:
            response = httpx.post(
                url,
                headers={"xi-api-key": self.settings.elevenlabs_api_key, "Content-Type": "application/json"},
                json={
                    "text": text,
                    "model_id": self.settings.elevenlabs_model_id,
                    "output_format": "mp3_44100_128",
                },
                timeout=60,
            )
            response.raise_for_status()
        except httpx.HTTPError as error:
            detail = error.response.text[:800] if isinstance(error, httpx.HTTPStatusError) else str(error)
            raise NarrationFailure(f"The ElevenLabs request failed: {detail}") from error

        data = response.json()
        alignment = data.get("normalized_alignment") or data.get("alignment")
        if not alignment:
            raise NarrationFailure("ElevenLabs returned no timestamps.")
        characters = alignment.get("characters", [])
        starts = alignment.get("character_start_times_seconds", [])
        ends = alignment.get("character_end_times_seconds", [])
        if not characters or len(characters) != len(starts) or len(starts) != len(ends):
            raise NarrationFailure("The ElevenLabs timestamps are incomplete.")

        aligned_text = "".join(characters)
        # The endpoint normally aligns the original text. If normalization changes length,
        # distribute section timing by narration character proportions rather than guessing indices.
        if len(aligned_text) == len(text):
            durations = [max(1.0, ends[min(end - 1, len(ends) - 1)] - starts[min(start, len(starts) - 1)]) for start, end in spans]
        else:
            total = ends[-1]
            total_chars = sum(max(1, end - start) for start, end in spans)
            durations = [max(1.0, total * max(1, end - start) / total_chars) for start, end in spans]

        return NarrationPackage(
            audio=base64.b64decode(data["audio_base64"]),
            text=text,
            section_durations=durations,
            srt=self._to_srt(aligned_text, starts, ends),
        )

    @staticmethod
    def _joined_text(sections: list[StoryboardSection]) -> tuple[str, list[tuple[int, int]]]:
        parts: list[str] = []
        spans: list[tuple[int, int]] = []
        cursor = 0
        for section in sections:
            narration = section.narration.strip()
            if parts:
                parts.append("\n\n")
                cursor += 2
            start = cursor
            parts.append(narration)
            cursor += len(narration)
            spans.append((start, cursor))
        return "".join(parts), spans

    @classmethod
    def _to_srt(cls, text: str, starts: list[float], ends: list[float]) -> str:
        words = list(re.finditer(r"\S+", text))
        if not words:
            return ""
        groups: list[list[re.Match[str]]] = []
        current: list[re.Match[str]] = []
        for word in words:
            proposed = current + [word]
            phrase = " ".join(item.group(0) for item in proposed)
            start_time = starts[min(proposed[0].start(), len(starts) - 1)]
            end_time = ends[min(proposed[-1].end() - 1, len(ends) - 1)]
            should_break = current and (
                len(proposed) > 7
                or len(phrase) > 44
                or end_time - start_time > 3.6
                or current[-1].group(0).endswith((".", "?", "!"))
            )
            if should_break:
                groups.append(current)
                current = [word]
            else:
                current = proposed
        if current:
            groups.append(current)

        lines: list[str] = []
        for index, group in enumerate(groups, start=1):
            start = starts[min(group[0].start(), len(starts) - 1)]
            end = ends[min(group[-1].end() - 1, len(ends) - 1)]
            phrase = " ".join(item.group(0) for item in group)
            lines.extend([str(index), f"{cls._timestamp(start)} --> {cls._timestamp(end)}", phrase, ""])
        return "\n".join(lines)

    @staticmethod
    def _timestamp(seconds: float) -> str:
        millis = int(round(seconds * 1000))
        hours, millis = divmod(millis, 3_600_000)
        minutes, millis = divmod(millis, 60_000)
        secs, millis = divmod(millis, 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"

