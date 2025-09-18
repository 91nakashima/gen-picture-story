from __future__ import annotations

from typing import Dict, Tuple

from app.config.settings import get_settings
from app.services.image_service import generate_image
from app.services.tts_service import generate_tts
from app.services.llm_service import build_image_prompt
from app.pipelines.compose_video import compose_scene_video, SceneMedia


def process_scene(image: bytes, audio: bytes) -> Dict[str, str]:
    """
    画像と音声（各1本）から単一シーン動画を合成する。

    備考:
        内部では `SceneMedia(image=[image], audio=[audio])` を用いて
        `compose_scene_video` を呼び出し、単一の辞書を返す。
    Returns:
        出力動画情報の辞書
    """
    media = SceneMedia(image=[image], audio=[audio])
    # 日本語コメント: 単一シーンでも compose_scene_video は単一の辞書を返す
    return compose_scene_video(media)


def narration_from_scene_text(scene_text: str, voice: str | None = None, fmt: str = "mp3") -> bytes:
    """Convert scene text to narration audio bytes via TTS."""
    s = get_settings()
    return generate_tts(scene_text, voice=voice or s.tts_voice, fmt=fmt)  # type: ignore[arg-type]


def image_from_scene_text(scene_text: str, image_size: str | None = None) -> Tuple[str, bytes]:
    """Generate an image from scene text via prompt refinement.

    Returns a tuple of (prompt, image_bytes).
    """
    s = get_settings()
    prompt = build_image_prompt(scene_text)
    img_bytes = generate_image(prompt=prompt, size=image_size or s.default_image_size)
    return prompt, img_bytes
