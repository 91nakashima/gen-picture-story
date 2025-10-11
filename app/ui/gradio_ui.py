from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO
from pathlib import Path
from typing import cast

import gradio as gr
from PIL import Image

from app.config.settings import get_settings
from app.services.story_service import (
    ImageAspectLiteral,
    StoryGenerationOptions,
    generate_from_story,
)


def _coerce_max_scenes(value: str | int | float | None) -> int | None:
    """UI入力から max_scenes の実値を決定するヘルパー。"""
    if value is None:
        return None

    normalized = str(value).strip().lower()
    if normalized in {"", "none", "制限なし"}:
        return None

    try:
        return int(float(normalized))
    except ValueError:
        return None


def _load_reference_images(files: Sequence[object] | None) -> list[bytes]:
    """Gradio ファイル入力から PNG バイト列を抽出する。"""
    if not files:
        return []

    allowed_mime = {"image/png", "image/jpeg"}
    result: list[bytes] = []
    for item in files:
        path_obj = getattr(item, "path", None)
        mime_obj = getattr(item, "mime_type", None)
        if isinstance(item, dict):
            item_dict = cast(dict[str, object], item)
            if path_obj is None:
                candidate_path = item_dict.get("path")
                if isinstance(candidate_path, str):
                    path_obj = candidate_path
            if mime_obj is None:
                candidate_mime = item_dict.get("mime_type")
                if isinstance(candidate_mime, str):
                    mime_obj = candidate_mime

        path = path_obj if isinstance(path_obj, str) else None
        mime = mime_obj if isinstance(mime_obj, str) else None

        if path is None:
            continue

        if mime and mime not in allowed_mime:
            # MIME が許容外の場合でも拡張子が jpeg/png なら許容
            suffix = path.lower()
            if not suffix.endswith((".jpg", ".jpeg", ".png")):
                continue

        try:
            data = Path(path).read_bytes()
        except Exception:
            continue

        try:
            with Image.open(BytesIO(data)) as img:
                with BytesIO() as buf:
                    img.convert("RGBA").save(buf, format="PNG")
                    result.append(buf.getvalue())
        except Exception:
            continue

    return result


def _split_multiline_text(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    lines = [line.strip() for line in value.replace("\r", "\n").split("\n")]
    return tuple(line for line in lines if line)


def _generate_story(
    story: str,
    max_scenes_value: str | int | float | None,
    image_size: ImageAspectLiteral,
    reference_files: Sequence[object] | None,
    local_images_text: str | None,
    http_images_text: str | None,
) -> tuple[str, str, str, str]:
    """Gradio コールバック用のラッパー。"""
    max_scenes = _coerce_max_scenes(max_scenes_value)
    refs = _load_reference_images(reference_files)
    options = StoryGenerationOptions(
        reference_images=tuple(refs),
        local_images=_split_multiline_text(local_images_text),
        http_images=_split_multiline_text(http_images_text),
    )
    return generate_from_story(
        story,
        max_scenes=max_scenes,
        image_size=image_size,
        options=options,
    )


def build_ui() -> gr.Blocks:
    s = get_settings()
    with gr.Blocks(title="Gen Picture Story") as demo:
        gr.Markdown(
            "# 画像 + 音声 → 動画 生成（MVP）\nOpenAI API + GCS + Cloud Run 前提の試作版"
        )

        with gr.Row():
            gr.Textbox(label="プロジェクト名", placeholder="例: my-story-001")
            max_scenes = gr.Dropdown(
                choices=[
                    "制限なし",
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "8",
                    "10",
                ],
                value="制限なし",
                label="最大シーン数",
            )
        story = gr.Textbox(lines=8, label="物語テキスト")

        with gr.Row():
            # 日本語コメント: デフォルトの画像サイズは 1024x576 に固定
            image_size = gr.Dropdown(
                choices=["1024x576", "1024x1024", "576x1024", "1920x1080", "1080x1920"],
                value="1024x576",
                label="画像サイズ",
            )
            gr.Textbox(value=s.tts_voice, label="TTSボイス")

        reference_images = gr.File(
            label="参考画像（任意, 複数可）",
            file_count="multiple",
            file_types=[".png", ".jpg", ".jpeg"],
        )
        local_images_text = gr.Textbox(
            label="参考画像のローカルパス（改行区切り, 任意）",
            placeholder="/path/to/image1.png\n/path/to/image2.jpg",
            lines=3,
        )
        http_images_text = gr.Textbox(
            label="参考画像のURL（改行区切り, 任意）",
            placeholder="https://example.com/image1.png\nhttps://example.com/image2.jpg",
            lines=3,
        )

        generate_btn = gr.Button("生成")

        with gr.Group():
            prompt_out = gr.Textbox(label="生成プロンプト（画像）")
            image_url = gr.Textbox(label="画像URL（署名付き）")
            audio_url = gr.Textbox(label="音声URL（署名付き）")
            video_url = gr.Textbox(label="動画URL（署名付き）")

        generate_btn.click(
            _generate_story,
            inputs=[
                story,
                max_scenes,
                image_size,
                reference_images,
                local_images_text,
                http_images_text,
            ],
            outputs=[prompt_out, image_url, audio_url, video_url],
        )

    return demo
