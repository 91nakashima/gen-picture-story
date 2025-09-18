from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional
import tempfile
import os

import ffmpeg

from app.config.settings import get_settings
from app.storage import gcs
from app.utils.env import env_truthy, outputs_root
from app.utils.log import log


def _final_dir(project: str) -> Path:
    """最終出力ディレクトリを返します。テスト時は repo 配下の outputs を使用。"""
    root = outputs_root() if env_truthy("PYTEST", "0") else (Path("/tmp") / "projects")
    return root / project / "final"


def _probe_audio_duration_sec(path: str) -> float | None:
    """ffprobe を用いて音声の長さ（秒）を取得します。取得できなければ None。"""
    try:
        info = ffmpeg.probe(path)
    except ffmpeg.Error:
        return None

    # format > duration が最も信頼できる
    fmt = info.get("format") or {}
    dur = fmt.get("duration")
    if isinstance(dur, str):
        try:
            return max(0.0, round(float(dur), 3))
        except ValueError:
            pass

    # stream 側の duration をフォールバックで探す
    for st in info.get("streams", []) or []:
        if st.get("codec_type") == "audio":
            sd = st.get("duration")
            if isinstance(sd, str):
                try:
                    return max(0.0, round(float(sd), 3))
                except ValueError:
                    continue
    return None


def compose_scene_video(
    project: str,
    idx: int,
    image: bytes | None = None,
    audio: bytes | None = None,
    *,
    image_path: str | None = None,
    audio_path: str | None = None,
    bucket_name: Optional[str] = None,
) -> Dict[str, str]:
    """
    静止画とナレーション音声から MP4 を合成します。

    ポイント:
    - 画像は `-loop 1`（静止画を動画化）
    - 音声の実長を ffprobe で取得し、出力 `-t` に指定して画像の表示時間と完全一致
    - 解像度は 1920x1080 にフィット（scale + pad、アスペクト維持）
    - H.264 + AAC、`+faststart` でストリーミング再生向け最適化
    """
    s = get_settings()
    out_dir = _final_dir(project)
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"scene_{idx:04d}.mp4"

    # 入力の正規化（bytes なら一時ファイルに書き出し、パスに統一）
    created_temp_paths: list[str] = []
    try:
        if image is not None and image_path is None:
            img_tmp = tempfile.NamedTemporaryFile(prefix=f"img_{idx:04d}_", suffix=".png", delete=False)
            img_tmp.write(image)
            img_tmp.flush()
            img_tmp.close()
            image_path = img_tmp.name
            created_temp_paths.append(image_path)
        if audio is not None and audio_path is None:
            aud_tmp = tempfile.NamedTemporaryFile(prefix=f"aud_{idx:04d}_", suffix=".mp3", delete=False)
            aud_tmp.write(audio)
            aud_tmp.flush()
            aud_tmp.close()
            audio_path = aud_tmp.name
            created_temp_paths.append(audio_path)

        if not image_path or not audio_path:
            raise ValueError("compose_scene_video requires either bytes or path for both image and audio")

        # 音声の実再生時間を取得（小数点3桁まで丸め）
        audio_dur = _probe_audio_duration_sec(audio_path)

        # 入力（画像）: ループして所定FPSでフレーム生成 → 1920x1080に整形
        v_in = (
            ffmpeg
            .input(image_path, loop=1, framerate=s.output_fps)
            .filter("scale", "1920", "1080", force_original_aspect_ratio="decrease")
            .filter("pad", "1920", "1080", "(ow-iw)/2", "(oh-ih)/2", color="black")
            .filter("setsar", "1")
        )

        # 入力（音声）: そのまま、必要に応じてサンプルレート/ビットレートを指定
        a_in = ffmpeg.input(audio_path).audio

        out_kwargs: dict[str, object] = dict(
            vcodec="libx264",
            acodec="aac",
            audio_bitrate="192k",
            ar="48000",  # 48kHz に正規化
            ac="2",      # ステレオに正規化（再生互換性向上）
            pix_fmt="yuv420p",
            r=s.output_fps,
            movflags="+faststart",
            video_bitrate="2000k",
        )

        # 音声長が取れた場合は -t を明示指定して、画像と音声の長さを完全一致させる
        if audio_dur is not None and audio_dur > 0:
            # ffmpeg-python の引数は文字列化して渡すのが無難
            out_kwargs["t"] = f"{audio_dur:.3f}"
        else:
            # 取得できない場合は -shortest で音声終端に合わせて自動終了
            out_kwargs["shortest"] = None

        (
            ffmpeg
            .output(v_in, a_in, str(out_path), **out_kwargs)
            .overwrite_output()
            .run(quiet=not env_truthy("PYTEST", "0"))
        )

        if env_truthy("PYTEST", "0"):
            # テスト時はローカル出力と file:// URL
            url = out_path.resolve().as_uri()
            log("[compose_scene_video] audio_dur=", audio_dur)
            log("[compose_scene_video] video_path=", str(out_path))
            return {
                "video_gcs": "",
                "video_url": url,
                "video_path": str(out_path),
            }
        else:
            # 本番は GCS へアップロード
            gcs_path = f"projects/{project}/final/scene_{idx:04d}.mp4"
            gcs_url = gcs.upload_file(
                gcs_path, str(out_path), content_type="video/mp4", bucket_name=bucket_name
            )
            signed = gcs.signed_url(gcs_path, bucket_name=bucket_name)
            return {
                "video_gcs": gcs_url,
                "video_url": signed,
                "video_path": str(out_path),
            }
    finally:
        # 作成した一時ファイルをクリーンアップ
        for p in created_temp_paths:
            try:
                os.remove(p)
            except Exception:
                pass
