from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass
from typing import Dict
import tempfile
import os
import time

import ffmpeg

from app.config.settings import get_settings
from app.utils.env import env_truthy, outputs_root
from app.utils.log import log


def _final_dir() -> Path:
    """最終出力ディレクトリを返します。テスト時は repo 配下の outputs を使用。"""
    root = outputs_root() if env_truthy("PYTEST", "0") else (Path("/tmp") / "projects")
    return root / "final"


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


@dataclass
class SceneMedia:
    """
    シーン動画の入力メディア（複数）を表すデータクラス。

    Params:
        image: 画像バイト列のリスト
        audio: 音声バイト列のリスト
    """
    image: list[bytes]
    audio: list[bytes]


def _compose_single_scene_video(image: bytes, audio: bytes) -> Dict[str, str]:
    """
    静止画1枚とナレーション音声1本から MP4 を1本合成する。

    - 画像は `-loop 1`（静止画を動画化）
    - 音声の実長を ffprobe で取得し、出力 `-t` に指定して画像と長さを完全一致
    - 解像度は 1920x1080 にフィット（scale + pad、アスペクト維持）
    - H.264 + AAC、`+faststart` でストリーミング再生向け最適化
    Returns:
        出力動画情報の辞書（video_path, video_url など）
    """
    s = get_settings()
    out_dir = _final_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / f"scene_{int(time.time())}.mp4"

    created_temp_paths: list[str] = []
    try:
        # image を一時ファイル化
        img_tmp = tempfile.NamedTemporaryFile(prefix="img_", suffix=".png", delete=False)
        img_tmp.write(image)
        img_tmp.flush()
        img_tmp.close()
        image_path = img_tmp.name
        created_temp_paths.append(image_path)

        # audio を一時ファイル化
        aud_tmp = tempfile.NamedTemporaryFile(prefix="aud_", suffix=".mp3", delete=False)
        aud_tmp.write(audio)
        aud_tmp.flush()
        aud_tmp.close()
        audio_path = aud_tmp.name
        created_temp_paths.append(audio_path)

        # 音声の実再生時間
        audio_dur = _probe_audio_duration_sec(audio_path)

        # 入力（画像）
        v_in = (
            ffmpeg
            .input(image_path, loop=1, framerate=s.output_fps)
            .filter("scale", "1920", "1080", force_original_aspect_ratio="decrease")
            .filter("pad", "1920", "1080", "(ow-iw)/2", "(oh-ih)/2", color="black")
            .filter("setsar", "1")
        )

        # 入力（音声）
        a_in = ffmpeg.input(audio_path)

        out_kwargs: dict[str, object] = dict(
            vcodec="libx264",
            acodec="aac",
            audio_bitrate="192k",
            ar="48000",
            ac="2",
            pix_fmt="yuv420p",
            r=s.output_fps,
            movflags="+faststart",
            video_bitrate="2000k",
        )

        if audio_dur is not None and audio_dur > 0:
            out_kwargs["t"] = f"{audio_dur:.3f}"
        else:
            out_kwargs["shortest"] = True

        (
            ffmpeg
            .output(v_in, a_in, str(out_path), **out_kwargs)
            .overwrite_output()
            .run(quiet=False)  # デバッグ時は False に
        )

        if env_truthy("PYTEST", "0"):
            url = out_path.resolve().as_uri()
            log("[_compose_single_scene_video] audio_dur=", audio_dur)
            log("[_compose_single_scene_video] video_path=", str(out_path))
            return {
                "video_gcs": "",
                "video_url": url,
                "video_path": str(out_path),
            }
        else:
            return {
                "video_gcs": "",
                "video_url": str(out_path),
                "video_path": str(out_path),
            }
    finally:
        for p in created_temp_paths:
            try:
                os.remove(p)
            except Exception:
                pass


def compose_scene_video(media: SceneMedia) -> Dict[str, str]:
    """
    複数の画像・音声の組を受け取り、各ペアから単一シーン動画を作成した後、
    それらを1本のMP4に連結して返す。

    Params:
        media: `image` と `audio` に各バイト列のリストを格納したデータクラス

    Returns:
        連結後の単一動画の出力情報（video_path, video_url など）
    """
    # 日本語コメント: 入力ペアごとに中間動画を作成
    segment_paths: list[str] = []
    first_result: Dict[str, str] | None = None
    for img, aud in zip(media.image, media.audio):
        seg = _compose_single_scene_video(img, aud)
        if first_result is None:
            first_result = seg
        segment_paths.append(seg["video_path"])

    # 日本語コメント: シーンが1つだけならそのまま返す
    if len(segment_paths) == 1:
        # 日本語コメント: 生成結果をそのまま返す
        return first_result or {"video_gcs": "", "video_url": segment_paths[0], "video_path": segment_paths[0]}

    # 日本語コメント: 複数シーンの場合は連結して単一MP4を返す
    return concat_videos(segment_paths)


def concat_videos(video_paths: list[str]) -> Dict[str, str]:
    """
    複数の動画ファイル（同一コーデック/パラメータ前提）を1本に連結する。

    - concat demuxer を使用（再エンコードなし）
    - すべての入力動画は同一のコーデック/サンプリングであることを推奨
    Returns:
        連結後の動画情報（video_path, video_url など）
    """
    out_dir = _final_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"concat_{int(time.time())}.mp4"

    # 入力リストファイルを作成
    list_file = tempfile.NamedTemporaryFile(prefix="concat_", suffix=".txt", mode="w", delete=False)
    try:
        for p in video_paths:
            # -safe 0 を使うので絶対パスやスペースにも対応
            list_file.write(f"file '{Path(p).resolve()}'\n")
        list_file.flush()
        list_file.close()

        (
            ffmpeg
            .input(list_file.name, f="concat", safe=0)
            .output(str(out_path), c="copy", movflags="+faststart")
            .overwrite_output()
            .run(quiet=False)
        )

        if env_truthy("PYTEST", "0"):
            url = out_path.resolve().as_uri()
            log("[concat_videos] video_path=", str(out_path))
            return {
                "video_gcs": "",
                "video_url": url,
                "video_path": str(out_path),
            }
        else:
            return {
                "video_gcs": "",
                "video_url": str(out_path),
                "video_path": str(out_path),
            }
    finally:
        try:
            os.remove(list_file.name)
        except Exception:
            pass
