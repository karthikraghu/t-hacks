from __future__ import annotations

import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from services.api.app.main import app  # noqa: E402


def require_ok(response, step: str) -> dict:  # type: ignore[no-untyped-def]
    if not response.is_success:
        raise RuntimeError(f"{step} fehlgeschlagen ({response.status_code}): {response.text}")
    return response.json()


def main() -> None:
    client = TestClient(app)
    health = require_ok(client.get("/health"), "Healthcheck")
    if not health["model_configured"] or not health["elevenlabs_configured"]:
        raise SystemExit("The model and ElevenLabs must be configured for the live smoke test.")

    payload = {
        "grade": 8,
        "topic_id": "linear-functions",
        "subtopic_id": "understanding-slope",
        "level": "standard",
        "method": "auto",
    }
    print("1/5 Creating the live storyboard ...", flush=True)
    storyboard = require_ok(client.post("/api/storyboards", json=payload), "Storyboard")
    original_ids = [section["id"] for section in storyboard["sections"]]
    print(f"    {len(storyboard['sections'])} sections, live={storyboard['generated_live']}", flush=True)

    target = storyboard["sections"][1]
    print("2/5 Revising exactly one section ...", flush=True)
    revised = require_ok(
        client.post(
            f"/api/storyboards/{storyboard['id']}/sections/{target['id']}/revise",
            json={"comment": "Please explain this step in one especially clear, short sentence."},
        ),
        "Abschnittsrevision",
    )
    if [section["id"] for section in revised["sections"]] != original_ids:
        raise RuntimeError("The section revision changed the stable section IDs.")
    for index, section in enumerate(revised["sections"]):
        if index != 1 and section != storyboard["sections"][index]:
            raise RuntimeError(f"The section revision unintentionally changed section {index + 1}.")

    print("3/5 Approving the storyboard and starting the media pipeline ...", flush=True)
    started_at = time.perf_counter()
    approval = require_ok(client.post(f"/api/storyboards/{storyboard['id']}/approve"), "Freigabe")
    job_id = approval["id"]

    terminal = {"ready", "failed", "cached_fallback"}
    while True:
        job = require_ok(client.get(f"/api/jobs/{job_id}"), "Jobstatus")
        if job["status"] in terminal:
            break
        if time.perf_counter() - started_at > 600:
            raise TimeoutError("The live job did not reach a terminal status within ten minutes.")
        time.sleep(1)
    elapsed = time.perf_counter() - started_at
    print(f"4/5 Final status: {job['status']} after {elapsed:.1f} seconds", flush=True)
    print(f"    {job['message']}", flush=True)
    if job["status"] != "ready":
        raise RuntimeError(f"The live pipeline did not finish successfully: {job['status']} - {job['message']}")

    expected = {"lesson.mp4", "recap_1.png", "recap_2.png", "recap_3.png"}
    names = {artifact["name"] for artifact in job["artifacts"]}
    if names != expected:
        raise RuntimeError(f"Unerwarteter Artefaktsatz: {sorted(names)}")
    for artifact in job["artifacts"]:
        response = client.get(artifact["url"])
        if not response.is_success or len(response.content) < 100:
            raise RuntimeError(f"Artefakt nicht abrufbar: {artifact['name']}")
    print("5/5 The MP4 and three PNGs are retrievable through the API.", flush=True)
    print(f"storyboard_id={storyboard['id']}", flush=True)
    print(f"job_id={job_id}", flush=True)


if __name__ == "__main__":
    main()
