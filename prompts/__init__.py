from __future__ import annotations

from openai.types.chat import (
    ChatCompletionFunctionToolParam,
    ChatCompletionNamedToolChoiceParam,
)

"""
プロンプト定義モジュール

各関数はLLMへ渡すシステムプロンプトを返します。
必要に応じて、このモジュールを編集・拡張してください。
"""


def split_scenes_system() -> str:
    """物語分割用のシステムプロンプトを返す。"""
    return (
        "You split a Japanese children story into concise scene chunks. "
        "Return results by calling the provided function with an array of scene texts."
    )


def image_prompt_system() -> str:
    """画像プロンプト生成用のシステムプロンプトを返す。"""
    return (
        "You turn a short Japanese scene into a concise, effective English image prompt for a picture book illustration. "
        "If a style hint is present, incorporate it. "
        "Favor concrete visual details (subjects, composition, mood, palette). "
        "For sequential scenes, explicitly ask to keep character design and style consistent across scenes."
    )


def return_scenes_tool() -> ChatCompletionFunctionToolParam:
    """Function-calling tool schema for returning split scenes.

    llm_service.split_scenes から参照されます。
    """
    return {
        "type": "function",
        "function": {
            "name": "return_scenes",
            "description": "物語を分割したシーン配列を返す",
            "parameters": {
                "type": "object",
                "properties": {
                    "scenes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "各シーンのテキスト配列",
                    }
                },
                "required": ["scenes"],
            },
        },
    }


def return_scenes_tool_choice() -> ChatCompletionNamedToolChoiceParam:
    """tool_choice for the return_scenes function.

    llm_service.split_scenes から参照されます。
    """
    return {"type": "function", "function": {"name": "return_scenes"}}
