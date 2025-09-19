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
        # (
        # "むかし、むかし、ある所におじいさんとおばあさんが住んでいました。"
        # "おじいさんは山へしば刈りに、おばあさんは川へ洗濯に行きました。"
        # "おばあさんが川で洗濯をしていると大きな桃が流れてきました。"
        # "「なんと大きな桃じゃろう！家に持って帰ろう。」"
        # "とおばあさんは背中に担いで家に帰り、その桃を切ろうとすると、なんと桃から大きな赤ん坊が出てきたのです。"
        # "「おっとたまげた。」"
        # "二人は驚いたけれども、とても喜びました。"
        # )

        # (
        #     "西暦2022年。"
        #     "次世代のVRMMORPG《ソードアート・オンライン》が正式にサービスを開始した日。"

        #     "桐ヶ谷和人――オンラインでは「キリト」と名乗る少年は、ログイン直後から胸を高鳴らせていた。"
        #     "フルダイブ技術で構築されたこの世界は、風が肌を撫で、石畳の感触が足裏に伝わる。まるで現実の延長線上にあるかのようだった。"

        #     "広大な浮遊城《アインクラッド》。その第一層《はじまりの街》の街並みを眺めながら、キリトは思わず笑みをこぼす。"
        #     "彼はβテストの参加者だったため、操作方法にも慣れており、初心者のプレイヤーに比べれば有利な立場にあった。"

        #     "そんな彼の前に現れたのが、少し不安げな顔をしたプレイヤー、クラインだった。"
        #     "「よぉ、兄ちゃん。操作、教えてくれないか？」"
        #     "人懐っこい笑みを浮かべる彼に、キリトはしばし迷った末、剣の扱い方やモンスターとの戦い方を教えることにする。"
        #     "二人は野原へと出て、スライムのような小型モンスターを相手に剣を振るった。"
        #     "「おおっ！　これが《ソードスキル》か！」"
        #     "感動するクラインを見て、キリトはどこか誇らしげに笑った。"
        # )

        """
        　陸上の世界選手権東京大会第6日は18日、国立競技場で行われた。男子400メートル決勝には、日本記録保持者の中島佑気ジョセフ（富士通）が出場。前回東京で開催された1991年大会の高野進（7位）以来、日本人にとって34年ぶりとなるファイナルを疾走し、44秒62で日本勢最高の6位に入った。

【動画】「速い速い！！」　中島佑気ジョセフが雨中でも猛追した実際の映像

　決勝の舞台に立つのがどれほど困難か。大観衆も知っているからこそ、中島の力走に国立が揺れた。大外9レーンから発進。大粒の雨が降る中、大歓声に乗って激走。高野進の7位を上回り、日本勢最高の6位に入った。

「決勝を目標にしてきて、ようやく夢に見てきた決勝を東京で走ることができて幸せだったけど、それより先に悔しい感情が出てきて。やっぱりメダルが取りたかった」

　14日の予選で従来の記録を一気に0秒33も更新する44秒44の日本新記録をマーク。16日の準決勝は300メートル通過が8選手中7番手ながら、怒涛の追い上げを見せて2着でフィニッシュ。この種目で高野進以来、34年ぶりの決勝進出を決めていた。

　準決勝は「前半少し抑えすぎた」と反省。「予選の前半のいい感じの乗りと、準決勝の後半の上がりを組み合わせて最高のレースをしたい」と誓い、夢舞台を駆け抜けた。
"""
    )

    assert isinstance(prompt, str) and len(prompt) > 0
    assert img_url.startswith("file://")
    assert aud_url.startswith("file://")
    assert vid_url.startswith("file://")

    # 日本語コメント: 生成された動画の物理ファイルが存在することを確認
    vid_path = _path_from_file_url(vid_url)
    assert vid_path.is_file()
