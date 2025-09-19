from __future__ import annotations

import base64
import json
from typing import Optional, Any, cast
from urllib import request

from openai import OpenAI

from app.config.settings import get_settings
from app.utils.log import log


def generate_image(
    prompt: str,
    size: str | None = None,
    images: list[bytes] | None = None,
) -> bytes:
    """
    画像を生成してPNGのバイト列を返す（OpenRouter 経由の画像モデル）。

    引数:
        prompt: 生成用のテキストプロンプト。
        size: 画像サイズ（例: "1024x576", "1024x1024"）。未指定時は "1024x576"。
        images: 参照用の入力画像（最大5枚）。PNGのバイト列のリスト。
                Chat Completions の画像入力フォーマットに合わせ、
                data URL（data:image/png;base64, ...）として送信します。
    戻り値:
        PNG のバイト列。
    """

    s = get_settings()
    # サイズ指定があればプロンプト末尾にフラグ形式で付加
    w, h = _parse_wh(size, "1024x576")
    prompt_with_size = f"{prompt} --width {w} --height {h}"
    # 日本語コメント: 参照画像がある場合は「一貫性を保ちつつ重複を避ける」指示を付加
    if images:
        prompt_with_size += (
            " Maintain character identity, color palette, and illustration style consistent with the reference images; "
            "however, do NOT replicate previous compositions. Create a distinct new scene: vary pose, background, camera angle, lighting, and framing. "
            "Avoid exact repeats of layouts, backgrounds, or object arrangements."

            # 日本語コメント: 参照画像がある場合は「一貫性を保ちつつ重複を避ける」指示を付加
            # 参照画像と一貫性を保ちつつ重複を避けてください。
            # 新しいシーンを作成してください: ポーズ、背景、カメラアングル、照明、フレーミングを変えてください。
            # レイアウト、背景、オブジェクトの配置の正確な繰り返しは避けてください。
        )

    # 日本語コメント: 参照画像を最大5枚まで組み立て
    content_items: list[dict[str, Any]] = [{"type": "text", "text": prompt_with_size}]
    if images:
        # 直近の5枚のみ使用
        refs: list[bytes] = list(images)[-5:]
        for im in refs:
            try:
                b64 = base64.b64encode(bytes(im)).decode("ascii")
                content_items.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                })
            except Exception:
                # 個別の添付失敗はスキップ（全体は継続）
                continue

    # オンライン実行（OpenAI SDK を使用して OpenRouter 経由で呼び出し）
    try:
        client = OpenAI(
            api_key=s.app_openrouter_api_key,
            base_url=s.app_openrouter_base_url,
        )
        # 非ストリームで取得し、辞書化してから画像を探す
        # 日本語コメント: 参照画像がある場合は content を配列形式で送る
        if images:
            # Pyright 型回避: content を配列形式にする
            messages_any: Any = [{"role": "user", "content": content_items}]
            resp = client.chat.completions.create(
                model=s.model_image,
                messages=cast(Any, messages_any),
            )
        else:
            resp = client.chat.completions.create(
                model=s.model_image,
                messages=[{"role": "user", "content": prompt_with_size}],
            )
        # 型付きオブジェクト → dict
        obj: dict
        if hasattr(resp, "model_dump"):
            obj = resp.model_dump()  # type: ignore[assignment]
        else:  # 予備
            try:
                obj = json.loads(resp.json())  # type: ignore[attr-defined]
            except Exception:
                obj = json.loads(getattr(resp, "to_json", lambda: "{}")())

        b = _extract_image_bytes_from_response(obj)
        if b:
            return b
    except Exception as e:  # ネットワーク遮断や予期しない例外
        # 明示的に失敗させ、テストで原因が見えるようにする
        log("[generate_image] openai client error:", str(e))
        raise

    # 画像が取得できなかった場合はエラー
    raise RuntimeError("No image bytes found in OpenRouter response")


def _parse_wh(size: Optional[str], default_size: Optional[str]) -> tuple[int, int]:
    s = (size or default_size or "").strip().lower()
    if "x" in s:
        try:
            w_s, h_s = s.split("x", 1)
            return max(1, int(w_s)), max(1, int(h_s))
        except Exception:
            pass
    return 1024, 1024


def _fetch_bytes(url: str, headers: dict[str, str] | None = None) -> bytes:
    req = request.Request(url, headers=headers or {}, method="GET")
    with request.urlopen(req) as r:
        return r.read()


def _extract_image_bytes_from_response(obj: dict) -> Optional[bytes]:
    # いくつかの候補パスを試す
    try:
        # chat.completions 形式
        choices = obj.get("choices") or []
        if choices:
            message = choices[0].get("message") or {}
            if message:
                images = message.get("images") or []
                for im in images:
                    b64 = im.get("b64_json") or (im.get("image") or {}).get("b64_json")
                    if b64:
                        return base64.b64decode(b64)
                    url = None
                    if isinstance(im.get("image_url"), dict):
                        url = im["image_url"].get("url")
                    elif isinstance(im.get("image"), dict):
                        url = im["image"].get("url")
                    if url:
                        return _fetch_bytes(url)
    except Exception:
        return None
    return None
