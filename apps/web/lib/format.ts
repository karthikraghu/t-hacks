export function timecode(totalSeconds: number): string {
  const whole = Math.max(0, Math.round(totalSeconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

export function sceneNumber(index: number): string {
  return String(index + 1).padStart(2, "0");
}

export function totalDuration(sections: { duration_seconds: number }[]): number {
  return sections.reduce((sum, section) => sum + section.duration_seconds, 0);
}

export function cumulativeStarts(sections: { duration_seconds: number }[]): number[] {
  let running = 0;
  return sections.map((section) => {
    const start = running;
    running += section.duration_seconds;
    return start;
  });
}
