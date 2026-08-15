# AI Micro-Lesson Studio

Local hackathon application for mathematics teachers at a German Gymnasium. A teacher configures a micro-lesson, reviews the AI storyboard, and generates a narrated Manim video plus three recap cards. The interface and the generated lessons are in English.

See [docs/SETUP.md](docs/SETUP.md) for a one-page map of the pieces and the end-to-end flow.

## Start locally

1. Copy `.env.example` to `.env`.
2. Set `MODEL_NAME`, the API key for the selected model provider, `ELEVENLABS_API_KEY`, and `ELEVENLABS_VOICE_ID`.
3. Install `uv`, Node.js 22+, and MiKTeX on the demo laptop.
4. From the repository root, create the local Python environment and install dependencies:

   ```powershell
   uv python install 3.12 --no-registry --no-bin
   uv venv --python 3.12 .venv
   uv pip install --python .venv\Scripts\python.exe -r services\api\requirements.txt
   npm install --prefix apps\web
   ```

5. Run `./scripts/check-prereqs.ps1` and allow MiKTeX to finish its first-run setup.
6. In one terminal run `./scripts/start-api.ps1`.
7. In another terminal run `./scripts/start-web.ps1`.
8. Open `http://localhost:3000`.

The frontend runs on port 3000 and the FastAPI service on port 8000. Manim runs as a local subprocess after AST validation. The subprocess receives a sanitized environment without model or ElevenLabs credentials.

Before the paid visual review runs, the preview render passes two deterministic gates. One compares the
animation length with the narration length so picture and speech cannot drift apart; the other extracts
one frame per lesson section and rejects any frame whose outer two percent contains lesson content, so
content cut off at a frame edge never depends on a model judgement. The lower band of the frame
(`y = -4.0` to `-3.0`) is kept clear for the captions FFmpeg burns in afterwards.

Docker is intentionally not required for the hackathon MVP. Run the four focused checks with:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_minimal_checks -v
```

After selecting the ElevenLabs voice, build the polished cached hero bundle once:

```powershell
.\.venv\Scripts\python.exe scripts\build_hero_fallback.py
```

Run the single paid end-to-end smoke path only when both providers are configured:

```powershell
.\.venv\Scripts\python.exe scripts\run_live_smoke.py
```

See [docs/plan.md](docs/plan.md) for the agreed scope and sprint plan.
