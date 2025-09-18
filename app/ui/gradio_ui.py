from __future__ import annotations

import gradio as gr

from app.config.settings import get_settings
from app.services.story_service import generate_from_story


def build_ui() -> gr.Blocks:
    s = get_settings()
    with gr.Blocks(title="Gen Picture Story") as demo:
        gr.Markdown("# 画像 + 音声 → 動画 生成（MVP）\nOpenAI API + GCS + Cloud Run 前提の試作版")

        with gr.Row():
            gr.Textbox(label="プロジェクト名", placeholder="例: my-story-001")
            max_scenes = gr.Slider(1, 5, value=1, step=1, label="最大シーン数（MVPは先頭のみ使用）")
        story = gr.Textbox(lines=8, label="物語テキスト")

        with gr.Row():
            gr.Dropdown(choices=["1024x576", "1024x1024", "768x1365"], value=s.default_image_size, label="画像サイズ")
            gr.Textbox(value=s.tts_voice, label="TTSボイス")

        generate_btn = gr.Button("生成")

        with gr.Group():
            prompt_out = gr.Textbox(label="生成プロンプト（画像）")
            image_url = gr.Textbox(label="画像URL（署名付き）")
            audio_url = gr.Textbox(label="音声URL（署名付き）")
            video_url = gr.Textbox(label="動画URL（署名付き）")

        # 実処理は (story, max_scenes) のみを引数に使用
        generate_btn.click(generate_from_story, inputs=[story, max_scenes], outputs=[prompt_out, image_url, audio_url, video_url])

    return demo
