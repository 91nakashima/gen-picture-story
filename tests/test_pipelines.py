from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.pipelines.generate_scene import process_scene
from app.pipelines.compose_video import compose_scene_video


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
    project = "pytest-demo"
    res = process_scene(
        project=project,
        idx=1,
        scene_text="静かな湖畔に小舟が浮かび、月が水面に映っている。",
        voice=None,
        image_size="1024x1024",
    )
    print("prompt:\n", res["prompt"])  # プロンプトを出力
    assert Path(res["image_path"]).is_file()
    assert Path(res["audio_path"]).is_file()


def test_compose_scene_video_local_outputs():
    """
    テスト概要: 生成済みの画像/音声から動画を合成し、outputs に保存されることを確認します。
    実行例: pytest -s tests/test_pipelines.py -k "test_compose_scene_video_local_outputs"
    """
    require_openai_key()

    # まずシーンの生成を行い、画像と音声を得る（実フローに合わせる）
    res = process_scene(
        project="pytest-demo",
        idx=1,
        scene_text="静かな湖畔に小舟が浮かび、月が水面に映っている。",
        voice=None,
        image_size="1024x1024",
    )
    img_path = Path(res["image_path"]).resolve()
    aud_path = Path(res["audio_path"]).resolve()
    assert img_path.is_file()
    assert aud_path.is_file()

    # 実際のフローに近づけるため、バイト列を渡す
    img_bytes = img_path.read_bytes()
    aud_bytes = aud_path.read_bytes()

    video = compose_scene_video(project=project, idx=1, image=img_bytes, audio=aud_bytes)
    print("video_path:", video["video_path"])  # 生成された動画のパス
    assert Path(video["video_path"]).is_file()
