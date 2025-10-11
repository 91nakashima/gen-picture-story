from __future__ import annotations

import os
from typing import Literal, Any
from pathlib import Path
import tempfile
from openai import OpenAI

from app.config.settings import get_settings
from app.utils.env import env_truthy
from app.utils.log import log
import ffmpeg as _ffmpeg  # type: ignore

ffmpeg: Any = _ffmpeg


def generate_tts(
    text: str,
    voice: str | None = None,
    fmt: Literal["mp3", "wav", "flac"] = "mp3",
    speed: Literal["slow", "middle", "fast"] = "middle",
) -> bytes:
    """
    音声を生成し、バイト列を返します（OpenAI の TTS を使用）。

    Params:
        text: 読み上げるテキスト
        voice: ボイス名（未指定時は設定値を使用）
        fmt: 出力音声フォーマット（mp3/wav/flac）
        speed: 話速（"slow" | "middle" | "fast"）。既定は "middle"。
    Returns:
        音声バイト列
    """

    s = get_settings()
    client = OpenAI(
        api_key=s.openai_api_key or os.getenv("OPENAI_API_KEY", ""),
        base_url=s.openai_base_url,
    )
    v = voice or s.tts_voice

    # 日本語コメント: まずは通常速度で音声ファイルを生成
    with tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=True) as tmp:
        with client.audio.speech.with_streaming_response.create(
            model=s.model_tts,
            voice=v,
            input=text,
            response_format=fmt,
        ) as response:
            response.stream_to_file(tmp.name)
        tmp.seek(0)
        if speed == "middle":
            # 日本語コメント: 中速はそのまま返す
            if env_truthy("PYTEST", "0"):
                log("[generate_tts] voice=", v, ", fmt=", fmt, ", speed=", speed)
                log("[generate_tts] text=\n", text)
            return tmp.read()

        # 日本語コメント: slow/fast の場合は ffmpeg の atempo で話速を調整
        atempo_map: dict[str, float] = {
            "slow": 0.85,
            "middle": 1.0,
            "fast": 1.25,
        }
        rate = atempo_map.get(speed, 1.0)

        # 日本語コメント: 出力用一時ファイル（エンコードに使用）
        out_tmp = tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False)
        out_tmp.close()
        try:
            # 日本語コメント: フォーマットに応じてコーデックを指定
            acodec: str
            if fmt == "mp3":
                acodec = "libmp3lame"
            elif fmt == "wav":
                acodec = "pcm_s16le"
            else:  # flac
                acodec = "flac"

            (
                ffmpeg.input(tmp.name)
                .filter("atempo", rate)
                .output(out_tmp.name, acodec=acodec, ar="48000", ac="2")
                .overwrite_output()
                .run(quiet=True)
            )

            data = Path(out_tmp.name).read_bytes()
            if env_truthy("PYTEST", "0"):
                log(
                    "[generate_tts] voice=",
                    v,
                    ", fmt=",
                    fmt,
                    ", speed=",
                    speed,
                    ", atempo=",
                    rate,
                )
                log("[generate_tts] text=\n", text)
            return data
        finally:
            try:
                os.remove(out_tmp.name)
            except Exception:
                pass
