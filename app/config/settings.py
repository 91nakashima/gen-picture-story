import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # OpenAI
    openai_api_key: str = os.getenv("AAP_OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # Model defaults
    model_llm: str = os.getenv("MODEL_LLM", "gpt-4o-mini")
    # 画像生成は OpenRouter 経由で Gemini を利用
    model_image: str = os.getenv("MODEL_IMAGE", "google/gemini-2.5-flash-image-preview")
    # model_image: str = os.getenv("MODEL_IMAGE", "google/gemini-2-5-flash-image-preview:free")
    model_tts: str = os.getenv("MODEL_TTS", "gpt-4o-mini-tts")
    tts_voice: str = os.getenv("TTS_VOICE", "alloy")

    # GCP
    # Base64-encoded service account JSON for explicit credentials
    # If set, code will decode and use it instead of ADC.
    gcp_sa_key_b64: str | None = os.getenv("GCP_SA_KEY_B64")
    # Optional: explicit GCP project ID override
    gcp_project: str | None = os.getenv("GCP_PROJECT")

    # App
    output_fps: int = int(os.getenv("OUTPUT_FPS", "30"))
    signed_url_expire_seconds: int = int(os.getenv("SIGNED_URL_EXPIRE_SECONDS", "86400"))

    # OpenRouter（画像生成用）
    # AAP系と通常の環境変数の両方に対応
    app_openrouter_api_key: str = (
        os.getenv("AAP_OPENROUTER_API_KEY")
        or os.getenv("OPENROUTER_API_KEY", "")
    )
    app_openrouter_base_url: str = (
        os.getenv("AAP_OPENROUTER_BASE_URL")
        or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    )


def get_settings() -> Settings:
    return Settings()
