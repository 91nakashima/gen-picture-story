from __future__ import annotations

import os
from typing import Literal

from app.config.settings import get_settings
from app.utils.env import env_truthy
from app.utils.log import log


def generate_tts(text: str, voice: str | None = None, fmt: Literal["mp3", "wav", "flac"] = "mp3") -> bytes:
    """音声を生成し、バイト列を返します（OpenAIのTTSを使用）。"""
    import tempfile
    from openai import OpenAI

    s = get_settings()
    client = OpenAI(
        api_key=s.openai_api_key or os.getenv("OPENAI_API_KEY", ""),
        base_url=s.openai_base_url
    )
    v = voice or s.tts_voice

    with tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=True) as tmp:
        with client.audio.speech.with_streaming_response.create(
            model=s.model_tts,
            voice=v,
            input=text,
            response_format=fmt,
        ) as response:
            response.stream_to_file(tmp.name)
        tmp.seek(0)
        if env_truthy("PYTEST", "0"):
            log("[generate_tts] voice=", v, ", fmt=", fmt)
            log("[generate_tts] text=\n", text)
        return tmp.read()
