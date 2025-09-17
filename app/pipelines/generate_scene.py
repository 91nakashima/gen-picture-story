from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from app.config.settings import get_settings
from app.services.image_service import generate_image
from app.services.tts_service import generate_tts
from app.services.llm_service import build_image_prompt
from app.storage import gcs
from app.utils.env import env_truthy, outputs_root
from app.utils.log import log


def _scene_dir(project: str, idx: int) -> Path:
    root = outputs_root() if env_truthy("PYTEST", "0") else (Path("/tmp") / "projects")
    return root / project / "scenes" / f"{idx:04d}"


def process_scene(
    project: str,
    idx: int,
    scene_text: str,
    voice: str | None = None,
    image_size: str | None = None,
    bucket_name: Optional[str] = None,
) -> Dict[str, str]:
    """Generate image and narration for a single scene, upload to GCS.

    Returns dict with gs:// paths and signed URLs.
    """
    s = get_settings()
    d = _scene_dir(project, idx)
    d.mkdir(parents=True, exist_ok=True)

    # Build image prompt (LLM refinement)
    prompt = build_image_prompt(scene_text)

    # Generate image (PNG bytes)
    img_bytes = generate_image(prompt=prompt, size=image_size or s.default_image_size)
    img_path = d / "image.png"
    img_path.write_bytes(img_bytes)

    # Generate narration (MP3)
    audio_bytes = generate_tts(scene_text, voice=voice or s.tts_voice, fmt="mp3")
    audio_path = d / "narration.mp3"
    audio_path.write_bytes(audio_bytes)

    if env_truthy("PYTEST", "0"):
        # テスト時はローカル出力を使用し、URLは file:// を返す
        url_img = img_path.resolve().as_uri()
        url_audio = audio_path.resolve().as_uri()
        log("[process_scene] prompt=\n", prompt)
        log("[process_scene] image_path=", str(img_path))
        log("[process_scene] audio_path=", str(audio_path))
        return {
            "image_gcs": "",
            "audio_gcs": "",
            "image_url": url_img,
            "audio_url": url_audio,
            "image_path": str(img_path),
            "audio_path": str(audio_path),
            "prompt": prompt,
        }
    else:
        # Upload to GCS (本番)
        scene_prefix = f"projects/{project}/scenes/{idx:04d}"
        gcs_img = gcs.upload_file(
            f"{scene_prefix}/image.png",
            str(img_path),
            content_type="image/png",
            bucket_name=bucket_name,
        )
        gcs_audio = gcs.upload_file(
            f"{scene_prefix}/narration.mp3",
            str(audio_path),
            content_type="audio/mpeg",
            bucket_name=bucket_name,
        )

        # Signed URLs
        url_img = gcs.signed_url(f"{scene_prefix}/image.png", bucket_name=bucket_name)
        url_audio = gcs.signed_url(f"{scene_prefix}/narration.mp3", bucket_name=bucket_name)

        return {
            "image_gcs": gcs_img,
            "audio_gcs": gcs_audio,
            "image_url": url_img,
            "audio_url": url_audio,
            "image_path": str(img_path),
            "audio_path": str(audio_path),
            "prompt": prompt,
        }
