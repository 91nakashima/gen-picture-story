from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse, unquote

import pytest

from app.services.story_service import generate_from_story


def require_openai_key() -> None:
    """
    日本語コメント: OpenAI APIキーが未設定の場合、このテストをスキップします。
    """
    if not os.getenv("AAP_OPENAI_API_KEY"):
        pytest.skip("AAP_OPENAI_API_KEY が未設定のためスキップ")


def _path_from_file_url(url: str) -> Path:
    """
    日本語コメント: file:// URL からローカルパスを取得するユーティリティ。
    """
    p = urlparse(url)
    return Path(unquote(p.path))


def test_generate_from_story_local_outputs(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    テスト概要: 物語テキストから画像・音声・動画を生成し、テスト時用のローカルURLが返ることを確認します。
    実行例: pytest -s tests/test_story_service.py -k "test_generate_from_story_local_outputs"
    """
    require_openai_key()
    # 日本語コメント: テストモードを有効化し、ローカル出力と file:// URL を得る
    monkeypatch.setenv("PYTEST", "1")

    prompt, img_url, aud_url, vid_url = generate_from_story(
        (
            "むかし、むかし、ある所におじいさんとおばあさんが住んでいました。"
            "おじいさんは山へしば刈りに、おばあさんは川へ洗濯に行きました。"
            "おばあさんが川で洗濯をしていると大きな桃が流れてきました。"
            "「なんと大きな桃じゃろう！家に持って帰ろう。」"
            "とおばあさんは背中に担いで家に帰り、その桃を切ろうとすると、なんと桃から大きな赤ん坊が出てきたのです。"
            "「おっとたまげた。」"
            "二人は驚いたけれども、とても喜び、"
            "「何という名前にしましょうか。」"
            "「桃から生まれたから、桃太郎というのはどうだろう。」"
            "「それがいい。」"
            "桃太郎はあっと言う間に大きくなり、立派な優しい男の子になりました。"
        )

    )

    assert isinstance(prompt, str) and len(prompt) > 0
    assert img_url.startswith("file://")
    assert aud_url.startswith("file://")
    assert vid_url.startswith("file://")

    # 日本語コメント: 生成された動画の物理ファイルが存在することを確認
    vid_path = _path_from_file_url(vid_url)
    assert vid_path.is_file()
