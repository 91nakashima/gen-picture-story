from __future__ import annotations

from typing import Dict, Tuple

from app.config.settings import get_settings
from app.services.image_service import generate_image
from app.services.tts_service import generate_tts
from app.services.llm_service import build_image_prompt
from app.pipelines.compose_video import compose_scene_video


def process_scene(image: bytes, audio: bytes) -> Dict[str, str]:
    """Compose a single-scene video from image/audio bytes only.

    - Avoids persisting image/audio; only composes a video.
    - During tests (PYTEST=1), writes the resulting MP4 under outputs/local.
    - Returns dict with video_path and URL (file:// when testing).
    """
    return compose_scene_video(image=image, audio=audio)


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
