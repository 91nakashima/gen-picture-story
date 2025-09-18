from __future__ import annotations

import time
from typing import Tuple, List

from app.config.settings import get_settings
from app.services.llm_service import split_scenes, build_image_prompt
from app.services.image_service import generate_image
from app.services.tts_service import generate_tts
from app.pipelines.compose_video import compose_scene_video, SceneMedia
from app.utils.env import env_truthy, outputs_root


def generate_from_story(story: str, max_scenes: int | None = None) -> Tuple[str, str, str, str]:
    """
    物語テキストからシーンを分割し、各シーンごとに画像と音声を生成する。
    すべてのシーンを1本のMP4動画に連結し、そのURLを返す。

    Params:
        story: 物語テキスト
        max_scenes: 最大シーン数（未指定時は無限扱い）
    Returns:
        (先頭シーンの生成プロンプト, 先頭シーンの画像URL, 先頭シーンの音声URL, 単一の動画URL)
    備考:
        - image_size と voice は設定値（settings）を使用
        - テスト時(PYTEST=1)のみ各シーンの画像・音声をローカル保存し、先頭シーンのURLを返す
    """
    s = get_settings()

    # シーン分割
    eff_max = max_scenes if max_scenes is not None else 9999
    scenes = split_scenes(story or "", max_scenes=eff_max)
    if not scenes:
        scenes = [story or ""]

    # 各シーンのアセット生成（バイト列）
    prompts: List[str] = []
    images: List[bytes] = []
    audios: List[bytes] = []

    # テスト時のみ画像/音声を書き出してURLを返す
    img_url = ""
    aud_url = ""

    project = f"proj-{int(time.time())}"
    for idx, scene_text in enumerate(scenes, start=1):
        # 日本語コメント: 画像/音声生成
        prompt = build_image_prompt(scene_text)

        # 日本語コメント: 画像生成は最大3回までリトライ
        image_bytes = b""
        for attempt in range(1, 3 + 1):
            try:
                image_bytes = generate_image(prompt, size=s.default_image_size)
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
