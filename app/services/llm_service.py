from __future__ import annotations

import json
import re
from typing import List, TypedDict, Any

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
    voice_script_system,
)


class SceneSpec(TypedDict):
    """シーン仕様（本文 + 各種ヒント）。"""
    text: str
    image_hint: str
    voice_hint: str
    voice_script: str
    sfx_hint: str


def split_scenes(text: str, max_scenes: int = 5) -> List[SceneSpec]:
    """
    LLMを用いて物語テキストを最大N個のシーンへ分割する。

    Params:
        text: 物語テキスト（日本語）
        max_scenes: 分割するシーンの最大数
    Returns:
        シーン仕様の配列（空でないことを保証）。各要素は以下のキーを持つ:
        - text: シーン本文（日本語）
        - image_hint: 推奨される画の方向性（構図/被写体/スタイル等）
        - voice_hint: 推奨ナレーション（話者/トーン/テンポ/言語等）
        - sfx_hint: 推奨効果音（現状は参照のみ; 実生成には未使用）
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
        f"以下の日本語テキストを、自然なまとまりで最大{max_scenes}個に分割してください。"
        "各シーンには、本文(text)、画像のヒント(image_hint)、ナレーションのスタイルヒント(voice_hint)、"
        "実際に読み上げるセリフ(voice_script)、効果音のヒント(sfx_hint)を含めてください。"
        "voice_script は日本語で1〜3文。背景説明・心情解説・SFX/BGM・カメラ指示は含めないでください。"
        "特に重要: すべての voice_script を先頭から順に連結しても、不自然な繰り返し（例:『私は〜です。私は〜です。』の連続）にならないように、"
        "前の内容を前提とした代名詞や接続表現を使って、文脈が自然につながるように書いてください。"
        "無理にシーンを区切って、句点ですぐに終わるようにしないでください。"
        "返答は用意された関数を必ず呼び出してください。\n\n"
        f"テキスト:\n{text}"
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
        scenes_raw: list[Any]
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
            scenes_raw = data.get("scenes", [])
        else:
            # フォールバック: 通常のテキストをJSONとして解釈
            content = choice.message.content or "[]"
            if env_truthy("PYTEST", "0"):
                log("[split_scenes/fallback] raw=\n", content)
            scenes_raw = json.loads(content)

        return _ensure_scene_specs(scenes_raw, text)
    except Exception:
        return _ensure_scene_specs([text], text)


def _ensure_scene_specs(scenes_raw: list[Any], original_text: str) -> List[SceneSpec]:
    """返却データを厳密な SceneSpec 配列へ正規化する。"""
    if not isinstance(scenes_raw, list) or not scenes_raw:
        return [SceneSpec(text=original_text, image_hint="", voice_hint="", voice_script="", sfx_hint="")]

    result: list[SceneSpec] = []
    for item in scenes_raw:
        if isinstance(item, str):
            t = item.strip()
            if t:
                result.append(SceneSpec(text=t, image_hint="",
                              voice_hint="", voice_script="", sfx_hint=""))
            continue
        if isinstance(item, dict):
            t = str(item.get("text", "")).strip()
            if not t:
                t = original_text
            image_hint = str(item.get("image_hint", "")).strip()
            voice_hint = str(item.get("voice_hint", "")).strip()
            voice_script = str(item.get("voice_script", "")).strip()
            sfx_hint = str(item.get("sfx_hint", "")).strip()
            result.append(SceneSpec(text=t, image_hint=image_hint,
                          voice_hint=voice_hint, voice_script=voice_script, sfx_hint=sfx_hint))

    return result or [SceneSpec(text=original_text, image_hint="", voice_hint="", voice_script="", sfx_hint="")]


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
        "次の内容を読み、最適なビジュアルスタイル指示を1行だけ返してください。"
        "日本語、読点で区切られた短い語句列で、10〜40文字程度に収めてください。\n\n"
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


def build_voice_script(scene_text: str, voice_hint: str | None = None) -> str:
    """
    シーン本文から、TTSに適した日本語のセリフ（ナレーション）を生成する。

    Params:
        scene_text: シーン本文（日本語）
        voice_hint: 話者/トーン/テンポ/フォーマリティなどの指示（任意）
    Returns:
        読み上げ用の短いセリフ（1〜3文程度）
    """
    s = get_settings()
    from openai import OpenAI
    client = OpenAI(
        api_key=s.openai_api_key or os.getenv("OPENAI_API_KEY", ""),
        base_url=s.openai_base_url,
    )

    system = voice_script_system()
    hint = (voice_hint or "").strip() or "ナレーション: 丁寧でわかりやすく、ゆっくりめ"
    user = (
        "以下のシーンから、TTS向けに『話すべきセリフ/ナレーションのみ』を短く作成してください。"
        "背景説明・心情解説・カメラ指示・効果音指示は含めないでください。"
        "引用符や括弧、ラベル（例: ナレーション:, BGM:, SFX:）も不要です。"
        "\n\nシーン:\n" + scene_text +
        "\n\n音声スタイル指示: " + hint +
        "\n\n出力は読み上げやすい日本語の短い文（1〜2文）だけを返してください。"
    )
    try:
        resp = client.chat.completions.create(
            model=s.model_llm,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.3,
        )
        content = (resp.choices[0].message.content or "").strip()
        if env_truthy("PYTEST", "0"):
            log("[build_voice_script] system=\n", system)
            log("[build_voice_script] user=\n", user)
            log("[build_voice_script] result=\n", content)
        return _sanitize_voice_script(content)
    except Exception:
        # フォールバック: シーン本文をそのまま使う
        return _sanitize_voice_script(scene_text)


def _sanitize_voice_script(text: str) -> str:
    """
    生成されたセリフから、背景描写や指示・括弧書きなどTTSに不要な記号/注釈を除去する。

    ルール:
        - 括弧（）()[]{}<> およびその中身を除去
        - 行頭のラベル（ナレーション:, Narrator:, BGM:, SFX:, 効果音:, SE:, カメラ: 等）を除去
        - ビジュアル記述を連想させるキーワード行を削除（背景:, 画面:, 映像:, シーン: など）
        - 文末重複の句読点を整理
        - 1〜2文に短縮
    """
    s = text.strip()
    # 括弧と中身を除去（全角・半角）
    bracket_patterns = [r"\(.*?\)", r"\[.*?\]", r"\{.*?\}", r"<.*?>", r"（.*?）", r"【.*?】", r"《.*?》"]
    for pat in bracket_patterns:
        s = re.sub(pat, "", s, flags=re.DOTALL)

    # 行単位の前置ラベル除去
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    cleaned_lines: list[str] = []
    label_re = re.compile(
        r"^(ナレーション|Narrator|BGM|SFX|SE|効果音|カメラ|Scene|シーン)\s*[:：]\s*", re.IGNORECASE)
    visual_prefix_re = re.compile(r"^(背景|画面|映像|シーン)\s*[:：]", re.IGNORECASE)
    for ln in lines:
        ln = label_re.sub("", ln)
        if visual_prefix_re.search(ln):
            continue
        cleaned_lines.append(ln)
    s = " ".join(cleaned_lines).strip()

    # 句点で文に分割し、1〜2文に制限
    # 日本語と混在する可能性に配慮して句点候補を広めに
    sentences = re.split(r"(?<=[。！？!?])\s+", s)
    sentences = [x.strip().strip('"\'') for x in sentences if x.strip()]
    if not sentences:
        return ""
    out = "".join(sentences[:2])
    # 句読点の過剰重複を軽減
    out = re.sub(r"[。]{2,}", "。", out)
    out = re.sub(r"[!！]{2,}", "！", out)
    out = re.sub(r"[?？]{2,}", "？", out)
    return out.strip()
