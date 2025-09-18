from __future__ import annotations

import time

import gradio as gr

from app.config.settings import get_settings
from app.services.llm_service import split_scenes
from app.services.llm_service import build_image_prompt
from app.services.image_service import generate_image
from app.services.tts_service import generate_tts
from app.pipelines.compose_video import compose_scene_video
from app.utils.env import env_truthy, outputs_root


def _generate(project: str, story: str, max_scenes: int, image_size: str, voice: str):
    s = get_settings()
    if not project:
        project = f"proj-{int(time.time())}"
    # Split scenes (use only the first for MVP)
    scenes = split_scenes(story or "", max_scenes=max_scenes or 1)
    scene_text = scenes[0] if scenes else (story or "")

    # Generate assets (bytes)
    prompt = build_image_prompt(scene_text)
    image_bytes = generate_image(prompt, size=image_size or None)
    audio_bytes = generate_tts(scene_text, voice=voice or s.tts_voice, fmt="mp3")

    # For UI: write image/audio only when testing so that URLs can be displayed
    img_url = ""
    aud_url = ""
    if env_truthy("PYTEST", "0"):
        d = (outputs_root() / project / "scenes" / f"{1:04d}")
        d.mkdir(parents=True, exist_ok=True)
        img_path = d / "image.png"
        aud_path = d / "narration.mp3"
        img_path.write_bytes(image_bytes)
        aud_path.write_bytes(audio_bytes)
        img_url = img_path.resolve().as_uri()
        aud_url = aud_path.resolve().as_uri()

    # Compose video
    video = compose_scene_video(image=image_bytes, audio=audio_bytes)

    # Outputs
    return (
        prompt,
        img_url,
        aud_url,
        video["video_url"],
    )


def build_ui() -> gr.Blocks:
    s = get_settings()
    with gr.Blocks(title="Gen Picture Story") as demo:
        gr.Markdown("# 画像 + 音声 → 動画 生成（MVP）\nOpenAI API + GCS + Cloud Run 前提の試作版")

        with gr.Row():
            project = gr.Textbox(label="プロジェクト名", placeholder="例: my-story-001")
            max_scenes = gr.Slider(1, 5, value=1, step=1, label="最大シーン数（MVPは先頭のみ使用）")
        story = gr.Textbox(lines=8, label="物語テキスト")

        with gr.Row():
            image_size = gr.Dropdown(choices=["1024x576", "1024x1024", "768x1365"], value=s.default_image_size, label="画像サイズ")
            voice = gr.Textbox(value=s.tts_voice, label="TTSボイス")

        generate_btn = gr.Button("生成")

        with gr.Group():
            prompt_out = gr.Textbox(label="生成プロンプト（画像）")
            image_url = gr.Textbox(label="画像URL（署名付き）")
            audio_url = gr.Textbox(label="音声URL（署名付き）")
            video_url = gr.Textbox(label="動画URL（署名付き）")

        generate_btn.click(_generate, inputs=[project, story, max_scenes, image_size, voice], outputs=[prompt_out, image_url, audio_url, video_url])

    return demo
