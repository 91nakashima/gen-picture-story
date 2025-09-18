from __future__ import annotations

import time
from typing import Tuple, List, Literal

from app.config.settings import get_settings
from app.services.llm_service import split_scenes, build_image_prompt, decide_style_hint
from app.services.image_service import generate_image
from app.services.tts_service import generate_tts
from app.pipelines.compose_video import compose_scene_video, SceneMedia
from app.utils.env import env_truthy, outputs_root


ImageAspectLiteral = Literal[
    # 横長（ランドスケープ）
    "1024x576",
    "1920x1080",
    # 縦長（ポートレート）
    "576x1024",
    "1080x1920",
    # 正方形
    "1024x1024",
]


def generate_from_story(
    story: str,
    max_scenes: int | None = None,
    image_size: ImageAspectLiteral = '1024x576',
) -> Tuple[str, str, str, str]:
    """
    物語テキストからシーンを分割し、各シーンごとに画像と音声を生成する。
    すべてのシーンを1本のMP4動画に連結し、そのURLを返す。

    Params:
        story: 物語テキスト
        max_scenes: 最大シーン数（未指定時は無限扱い）
        image_size: 画像の縦横比・解像度（リテラル）。
            - 横長: "1024x576", "1920x1080"
            - 縦長: "576x1024", "1080x1920"
            - 正方形: "1024x1024"
    Returns:
        (先頭シーンの生成プロンプト, 先頭シーンの画像URL, 先頭シーンの音声URL, 単一の動画URL)
    備考:
        - image_size 未指定時は "1024x576" を使用。voice は設定値を使用。
        - テスト時(PYTEST=1)のみ各シーンの画像・音声をローカル保存し、先頭シーンのURLを返す
    """
    if not story:
        raise ValueError("story must be non-empty")

    s = get_settings()
    # 日本語コメント: デフォルトは 1024x576
    eff_img_size = image_size

    # シーン分割
    eff_max = max_scenes if max_scenes is not None else 9999
    scenes = split_scenes(story, max_scenes=eff_max)
    if not scenes:
        scenes = [story or ""]

    # 日本語コメント: 物語/説明文の内容に応じて、スタイルヒントを自動決定
    style_global = decide_style_hint(story)

    # 各シーンのアセット生成（バイト列）
    prompts: List[str] = []
    images: List[bytes] = []
    audios: List[bytes] = []

    # テスト時のみ画像/音声を書き出してURLを返す
    img_url = ""
    aud_url = ""

    project = f"proj-{int(time.time())}"  # テスト用
    for idx, scene_text in enumerate(scenes, start=1):
        # 日本語コメント: 画像/音声生成
        # スタイルはストーリーに応じて可変（ビジネス説明/絵本/アニメ等）
        style_hint = style_global
        if idx > 1:
            style_hint = f"{style_global}、前のシーンと同一のキャラクターデザイン・配色・トーンを維持"
        prompt = build_image_prompt(scene_text, style_hint=style_hint)

        # 日本語コメント: 画像生成は最大3回までリトライ
        image_bytes = b""
        for attempt in range(1, 3 + 1):
            try:
                # 日本語コメント: 参照画像（最大5枚）で一貫性を補助 + 指定の縦横比で生成
                ref_images = images[-5:]
                image_bytes = generate_image(
                    prompt,
                    size=eff_img_size,
                    images=ref_images if ref_images else None,
                )
                break
            except Exception:  # ネットワークやAPIの一過性の失敗に対応
                if attempt >= 3:
                    raise
                time.sleep(0.8)

        # 日本語コメント: 音声生成は最大3回までリトライ
        audio_bytes = b""
        for attempt in range(1, 3 + 1):
            try:
                audio_bytes = generate_tts(scene_text, voice=s.tts_voice, fmt="mp3")
                break
            except Exception:
                if attempt >= 3:
                    raise
                time.sleep(0.8)

        prompts.append(prompt)
        images.append(image_bytes)
        audios.append(audio_bytes)

        # 日本語コメント: テスト時のみ、各シーンの画像/音声を書き出してURLを作成
        if env_truthy("PYTEST", "0"):
            d = (outputs_root() / project / "scenes" / f"{idx:04d}")
            d.mkdir(parents=True, exist_ok=True)
            img_path = d / "image.png"
            aud_path = d / "narration.mp3"
            img_path.write_bytes(image_bytes)
            aud_path.write_bytes(audio_bytes)
            if idx == 1:
                img_url = img_path.resolve().as_uri()
                aud_url = aud_path.resolve().as_uri()

    # 動画合成（全シーンを1本の動画に）
    media = SceneMedia(image=images, audio=audios)
    video = compose_scene_video(media)

    # 出力（先頭シーンの情報と、連結後の動画URL）
    return (
        prompts[0] if prompts else "",
        img_url,
        aud_url,
        video["video_url"],
    )
