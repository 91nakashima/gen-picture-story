from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.services.llm_service import build_image_prompt, split_scenes
from app.services.image_service import generate_image
from app.services.tts_service import generate_tts
from app.utils.env import outputs_root


# 日本語コメント: このテストは実際のOpenAI APIを呼び出します。
# 実行前に AAP_OPENAI_API_KEY を設定してください。
# 例: `export AAP_OPENAI_API_KEY=sk-...`


def require_openai_key() -> None:
    """
    実行に必要なAPIキーの有無を確認します。
    - LLM/TTS: AAP_OPENAI_API_KEY（OpenAI）
    - 画像生成: OPENROUTER_API_KEY（OpenRouter / Gemini）

    どちらも未設定の場合にスキップします。
    """
    if not (os.getenv("AAP_OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY")):
        pytest.skip("AAP_OPENAI_API_KEY または OPENROUTER_API_KEY が未設定のためスキップ")


def require_image_key() -> None:
    """画像生成に必要な OpenRouter の API キーを確認します。未設定ならスキップ。"""
    if not (os.getenv("OPENROUTER_API_KEY") or os.getenv("AAP_OPENROUTER_API_KEY")):
        pytest.skip("OPENROUTER_API_KEY または AAP_OPENROUTER_API_KEY が未設定のためスキップ")


def test_split_scenes_real():
    """
    テスト概要: 実際のストーリー分割を行い、配列が返ることを確認します。
    実行例: pytest -s tests/test_services.py -k "test_split_scenes_real"
    """

    require_openai_key()
    story = "むかしむかし、小さな村に太郎という少年が住んでいました。ある日、森で不思議な光を見つけました。"
    scenes = split_scenes(story, max_scenes=3)
    print("scenes:", scenes)
    assert isinstance(scenes, list)
    assert len(scenes) >= 1


def test_build_image_prompt_real():
    """
    テスト概要: 画像用の英語プロンプトが生成されることを確認します。
    実行例: pytest -s tests/test_services.py -k "test_build_image_prompt_real"
    """
    require_openai_key()
    prompt = build_image_prompt("青い鳥が朝焼けの空を飛ぶ")
    print("image prompt:", prompt)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_generate_image_real():
    """
    テスト概要: 実画像(PNG)を生成し、outputs ディレクトリへ保存します。
    画像生成は OpenRouter 経由で Gemini（google/gemini-2.5-flash-image-preview）を使用します。
    実行例: pytest -s tests/test_services.py -k "test_generate_image_real"
    """
    # 画像生成は OpenRouter を使用するため、専用キーを確認
    require_image_key()
    out_dir = outputs_root()
    out = out_dir / "test_image.png"
    img = generate_image("A vivid red apple on a white table, soft light", size="1024x1024")
    out.write_bytes(img)
    print("image path:", str(out))
    assert out.is_file() and out.stat().st_size > 0


def test_generate_tts_real(test_env, tmp_path: Path):
    """
    テスト概要: 実音声(MP3)を生成し、outputs ディレクトリへ保存します。
    実行例: pytest -s tests/test_services.py -k "test_generate_tts_real"
    """
    require_openai_key()
    out_dir = outputs_root()
    out = out_dir / "test_audio.mp3"
    audio = generate_tts("こんにちは。これはテスト音声です。落ち着いた声で読み上げてください。", voice=None, fmt="mp3")
    out.write_bytes(audio)
    print("audio path:", str(out))
    assert out.is_file() and out.stat().st_size > 0
