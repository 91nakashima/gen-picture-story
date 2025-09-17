from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import ffmpeg

from app.config.settings import get_settings
from app.storage import gcs
from app.utils.env import env_truthy, outputs_root
from app.utils.log import log


def _final_dir(project: str) -> Path:
    root = outputs_root() if env_truthy("PYTEST", "0") else (Path("/tmp") / "projects")
    return root / project / "final"


def compose_scene_video(
    project: str,
    idx: int,
    image_path: str,
    audio_path: str,
    *,
    bucket_name: Optional[str] = None,
) -> Dict[str, str]:
    """Compose a simple MP4 from a still image and narration audio.

    - Uses -loop 1 for still image, -shortest to end with audio length.
    """
    s = get_settings()
    out_dir = _final_dir(project)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"scene_{idx:04d}.mp4"

    (
        ffmpeg
        .input(image_path, loop=1, framerate=s.output_fps)
        .filter('scale', '1920:1080', 'force_original_aspect_ratio=decrease')
        .filter('pad', '1920', '1080', '(ow-iw)/2', '(oh-ih)/2', color='black')
        .output(
            ffmpeg.input(audio_path).audio,
            str(out_path),
            vcodec='libx264',
            acodec='aac',
            pix_fmt='yuv420p',
            r=s.output_fps,
            shortest=None,
            movflags='+faststart',
            video_bitrate='2000k',
        )
        .overwrite_output()
        .run(quiet=True)
    )

    if env_truthy("PYTEST", "0"):
        # テスト時はローカル出力と file:// URL
        url = out_path.resolve().as_uri()
        log("[compose_scene_video] video_path=", str(out_path))
        return {
            'video_gcs': '',
            'video_url': url,
            'video_path': str(out_path),
        }
    else:
        # 本番は GCS へアップロード
        gcs_path = f"projects/{project}/final/scene_{idx:04d}.mp4"
        gcs_url = gcs.upload_file(gcs_path, str(out_path), content_type='video/mp4', bucket_name=bucket_name)
        signed = gcs.signed_url(gcs_path, bucket_name=bucket_name)
        return {
            'video_gcs': gcs_url,
            'video_url': signed,
            'video_path': str(out_path),
        }
