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


def style_hint_system() -> str:
    """シーン全体のスタイル方針を決めるためのシステムプロンプトを返す。

    目的:
        入力された物語・説明文の内容から、映像・イラストの方向性を簡潔に指示するための
        日本語スタイルヒント（読点区切りの短い語句列）を1行で返す。

    要件:
        - 以下の代表カテゴリを参考に、最も適切な方向性を1つに集約して表現する
          例: 絵本風 / ビジネス向け説明動画 / アニメ風 / フォトリアル / 水彩風 / フラットデザイン
        - ビジネス向け説明は「フラットデザイン, プロフェッショナル, 落ち着いた配色, 図表・アイコン中心」などが適合
        - 子ども向け物語は「絵本風, 明るい色彩, やさしい雰囲気」などが適合
        - 出力は日本語、読点区切り、余計な文は書かない
        - シーン連続作品を想定し、キャラ・配色・トーンの一貫性が保てるような語彙を選ぶ
    """
    return (
        "You are a style director for visual generation. "
        "Read the Japanese story or explanatory text and return a single-line Japanese style hint "
        "(short phrases separated by '、'). "
        "Prefer concrete, high-level directives that help maintain consistency across sequential scenes."
    )
