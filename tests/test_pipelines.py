from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.pipelines.generate_scene import image_from_scene_text, narration_from_scene_text
from app.pipelines.compose_video import compose_scene_video, SceneMedia
from app.utils.env import outputs_root


# 日本語コメント: このテストは実際のOpenAI APIとFFmpegを使用します。
# 実行前に AAP_OPENAI_API_KEY を設定してください。
# FFmpeg バイナリがインストールされている必要があります。


def require_openai_key() -> None:
    if not os.getenv("AAP_OPENAI_API_KEY"):
        pytest.skip("AAP_OPENAI_API_KEY が未設定のためスキップ")


def test_process_scene_local_outputs():
    """
    テスト概要: プロジェクト 'pytest-demo' のシーン1を生成し、outputs に
    画像と音声が保存されることを確認します。
    実行例: pytest -s tests/test_pipelines.py -k "test_process_scene_local_outputs"
    """
    require_openai_key()
    # 画像と音声を個別に生成（保存はテスト時のみ行う）
    prompt, img_bytes = image_from_scene_text("静かな湖畔に小舟が浮かび、月が水面に映っている。", image_size="1024x1024")
    aud_bytes = narration_from_scene_text("静かな湖畔に小舟が浮かび、月が水面に映っている。")

    out_root = outputs_root() / "scenes" / f"{1:04d}"
    out_root.mkdir(parents=True, exist_ok=True)
    img_path = out_root / "image.png"
    aud_path = out_root / "narration.mp3"
    img_path.write_bytes(img_bytes)
    aud_path.write_bytes(aud_bytes)
    print("prompt:\n", prompt)  # プロンプトを出力
    assert img_path.is_file()
    assert aud_path.is_file()


def test_compose_scene_video_local_outputs():
    """
    テスト概要: 生成済みの画像/音声から動画を合成し、outputs に保存されることを確認します。
    実行例: pytest -s tests/test_pipelines.py -k "test_compose_scene_video_local_outputs"
    """
    require_openai_key()

    # 画像と音声を個別に生成して、バイト列で動画合成
    _, img_bytes = image_from_scene_text("静かな湖畔に小舟が浮かび、月が水面に映っている。", image_size="1024x1024")
    aud_bytes = narration_from_scene_text("静かな湖畔に小舟が浮かび、月が水面に映っている。")

    # img_bytesを保存
    img_path = outputs_root() / "local" / f"{1:04d}" / "image.png"
    img_path.parent.mkdir(parents=True, exist_ok=True)
    img_path.write_bytes(img_bytes)

    # aud_bytesを保存
    aud_path = outputs_root() / "local" / f"{1:04d}" / "narration.mp3"
    aud_path.parent.mkdir(parents=True, exist_ok=True)
    aud_path.write_bytes(aud_bytes)

    media = SceneMedia(image=[img_bytes], audio=[aud_bytes])
    video = compose_scene_video(media)
    print("video_path:", video["video_path"])  # 生成された動画のパス
    assert Path(video["video_path"]).is_file()
