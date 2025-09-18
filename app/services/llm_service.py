from __future__ import annotations

import json
from typing import List

import os
from app.config.settings import get_settings
from app.utils.env import env_truthy
from app.utils.log import log
from openai.types.chat import (
    ChatCompletionToolParam,
)
from prompts import (
    split_scenes_system,
    image_prompt_system,
    return_scenes_tool,
    return_scenes_tool_choice,
    style_hint_system,
)


def split_scenes(text: str, max_scenes: int = 5) -> List[str]:
    """
    LLMを用いて物語テキストを最大N個のシーンへ分割する。

    Params:
        text: 物語テキスト（日本語）
        max_scenes: 分割するシーンの最大数
    Returns:
        シーンのリスト（空でないことを保証）
    """
    s = get_settings()
    # OpenAI クライアントは関数内で生成（将来ライブラリ変更に備え局所化）
    from openai import OpenAI
    s = get_settings()
    client = OpenAI(
        api_key=s.openai_api_key or os.getenv("OPENAI_API_KEY", ""),
        base_url=s.openai_base_url
    )

    system = split_scenes_system()
    user = (
        f"以下の日本語の物語テキストを、自然なまとまりで最大{max_scenes}個に分割してください。"
        f"返答は用意された関数を必ず呼び出してください。\n\n{text}"
    )

    tools: list[ChatCompletionToolParam] = [return_scenes_tool()]

    try:
        resp = client.chat.completions.create(
            model=s.model_llm,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            tools=tools,
            tool_choice=return_scenes_tool_choice(),
        )

        choice = resp.choices[0]
        tool_calls = choice.message.tool_calls or []
        if tool_calls:
            tc0 = tool_calls[0]
            # Be defensive across OpenAI SDK versions: prefer duck-typing.
            func = getattr(tc0, "function", None)
            args_str = getattr(func, "arguments", None) or "{}"
            if env_truthy("PYTEST", "0"):
                log("[split_scenes/tools] system=\n", system)
                log("[split_scenes/tools] user=\n", user)
                log("[split_scenes/tools] args=\n", args_str)
            data = json.loads(args_str)
            scenes = data.get("scenes", [])
        else:
            # フォールバック: 通常のテキストをJSONとして解釈
            content = choice.message.content or "[]"
            if env_truthy("PYTEST", "0"):
                log("[split_scenes/fallback] raw=\n", content)
            scenes = json.loads(content)

        if not isinstance(scenes, list) or not scenes:
            return [text]
        scenes = [str(x).strip() for x in scenes if str(x).strip()]
        return scenes or [text]
    except Exception:
        return [text]


def build_image_prompt(scene_text: str, style_hint: str | None = None) -> str:
    """画像生成用の短い英語プロンプトを構築する。"""
    s = get_settings()
    # OpenAI クライアントは関数内で生成（将来ライブラリ変更に備え局所化）
    from openai import OpenAI
    s = get_settings()
    client = OpenAI(
        api_key=s.openai_api_key or os.getenv("OPENAI_API_KEY", ""),
        base_url=s.openai_base_url
    )
    style = style_hint or "絵本風, 明るい色彩, やさしい雰囲気"
    system = image_prompt_system()
    user = f"シーン:\n{scene_text}\n\nスタイル指示: {style}\n\n英語で画像プロンプトを作って"
    try:
        resp = client.chat.completions.create(
            model=s.model_llm,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.4,
        )
        content = (resp.choices[0].message.content or "").strip()
        if env_truthy("PYTEST", "0"):
            log("[build_image_prompt] system=\n", system)
            log("[build_image_prompt] user=\n", user)
            log("[build_image_prompt] result=\n", content)
        return content
    except Exception:
        # fallback: simple concatenation in English-ish
        return f"Picture book style, soft colors: {scene_text}"


def decide_style_hint(story_text: str) -> str:
    """
    物語または説明文から、最適なスタイルヒント（日本語、読点区切り、1行）を決定する。

    Params:
        story_text: 元となる物語・説明文（日本語）
    Returns:
        スタイルヒント文字列（例: "絵本風、明るい色彩、やさしい雰囲気"）
    """
    s = get_settings()
    # OpenAI クライアントは関数内で生成
    from openai import OpenAI
    client = OpenAI(
        api_key=s.openai_api_key or os.getenv("OPENAI_API_KEY", ""),
        base_url=s.openai_base_url,
    )

    system = style_hint_system()
    user = (
        "次の内容を読み、最適なビジュアルスタイル指示を1行だけ返してください。" \
        "日本語、読点で区切られた短い語句列で、10〜40文字程度に収めてください。\n\n" \
        f"本文:\n{story_text}"
    )
    try:
        resp = client.chat.completions.create(
            model=s.model_llm,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        content = (resp.choices[0].message.content or "").strip()
        if env_truthy("PYTEST", "0"):
            log("[decide_style_hint] system=\n", system)
            log("[decide_style_hint] user=\n", user)
            log("[decide_style_hint] result=\n", content)
        # 余計な改行や引用符を削る
        return content.splitlines()[0].strip("\"' ")
    except Exception:
        # 失敗時は保守的な既定値（絵本風）
        return "絵本風、明るい色彩、やさしい雰囲気"
