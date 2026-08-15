from functools import lru_cache
from pathlib import Path
import shutil

from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    model_provider: str = "openai"
    model_name: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""
    elevenlabs_model_id: str = "eleven_multilingual_v2"
    artifact_root: Path = REPO_ROOT / "jobs"
    catalog_path: Path = REPO_ROOT / "content" / "math" / "catalog.json"
    prompt_root: Path = REPO_ROOT / "prompts"
    fallback_root: Path = REPO_ROOT / "fallback"
    allow_hero_fallback: bool = True
    # Target size for a newly generated lesson. Deliberately small: a short lesson renders in
    # a fraction of the time, so the live path can be tested quickly and each section has room
    # to breathe. Raise these to produce longer lessons.
    lesson_target_sections: int = 2
    lesson_target_seconds: int = 30
    # Accepted range when validating any storyboard. Wider than the target so the bundled
    # five-section hero example still validates.
    lesson_min_sections: int = 2
    lesson_max_sections: int = 6
    lesson_min_seconds: int = 25
    lesson_max_seconds: int = 120
    manim_command: str = "manim"
    ffmpeg_command: str = "ffmpeg"
    # Per subprocess call, not per pipeline. A 100 second lesson renders at roughly 1.8x
    # realtime at -qm, so 180 seconds would kill a legitimate final render.
    render_timeout_seconds: int = 420

    @property
    def model_is_configured(self) -> bool:
        if not self.model_name:
            return False
        if self.model_provider == "openai":
            return bool(self.openai_api_key)
        if self.model_provider == "anthropic":
            return bool(self.anthropic_api_key)
        return False

    @property
    def elevenlabs_is_configured(self) -> bool:
        return bool(self.elevenlabs_api_key and self.elevenlabs_voice_id)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.manim_command == "manim":
        local_manim = REPO_ROOT / ".venv" / "Scripts" / "manim.exe"
        if local_manim.exists():
            settings.manim_command = str(local_manim)
    if settings.ffmpeg_command == "ffmpeg" and shutil.which("ffmpeg") is None:
        try:
            import imageio_ffmpeg

            settings.ffmpeg_command = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
    return settings
