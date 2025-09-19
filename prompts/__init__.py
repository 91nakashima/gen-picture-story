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
    """物語分割用のシステムプロンプトを返す。連続再生時の自然さを重視。"""
    return (
        "You act as a storyboarder and narration writer for a Japanese story or explainer. "
        "Split the input into concise, coherent scene chunks and provide fields for each scene. "
        "Crucially, the voice_script fields, when concatenated in order, must form a smooth, natural narration without redundant restatements. "
        "Avoid per‑scene reintroductions (e.g., repeating '私は〜です。' at every scene). "
        "Maintain consistent perspective, pronouns, and tense. Use connective devices to ensure flow between scenes."
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
            "description": "物語を分割したシーンの配列を返す（各シーンに画像/音声/効果音のヒントと、実際に読み上げるセリフを含む）",
            "parameters": {
                "type": "object",
                "properties": {
                    "scenes": {
                        "type": "array",
                        "description": "各シーンの仕様配列",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": "シーン本文（日本語、簡潔）",
                                },
                                "image_hint": {
                                    "type": "string",
                                    "description": "どんな画像（または動画カット）が良いかのヒント（構図・被写体・スタイル等）",
                                },
                                "voice_hint": {
                                    "type": "string",
                                    "description": "ナレーションのスタイルヒント（話者性別/トーン/テンポ/言語など）。実際のセリフは voice_script に記載。",
                                },
                                "voice_script": {
                                    "type": "string",
                                    "description": "実際に読み上げるセリフ（基本的に、背景説明・心情描写やSFX/BGM指示は含めない）",
                                },
                                "sfx_hint": {
                                    "type": "string",
                                    "description": "どんな効果音が良いか（将来用途、現状では使用しない）",
                                },
                            },
                            "required": ["text", "image_hint", "voice_hint", "voice_script", "sfx_hint"],
                        },
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


def voice_script_system() -> str:
    """TTS向けの日本語セリフ専用システムプロンプト（背景や心情の説明は禁止）。"""
    return (
        "You produce only spoken lines in Japanese suitable for TTS. "
        "Do NOT include visual descriptions, background, camera directions, emotions as labels, SFX/BGM notes, or stage directions. "
        "If the scene has dialogue, output polished dialogue lines only. If not, write 1–2 short narrator sentences that could be spoken aloud. "
        "No prefixes like 'ナレーション:' or character names unless strictly needed; avoid quotes and brackets. Keep it concise and readable."
    )
