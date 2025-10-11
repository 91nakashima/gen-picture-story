from __future__ import annotations

import base64
import json
from typing import Optional, Any, cast, Dict, List
from urllib import request

from openai import OpenAI

from app.config.settings import get_settings
from app.utils.log import log


def generate_image(
    prompt: str,
    size: str | None = None,
    base_images: list[bytes] | None = None,
    scene_images: list[bytes] | None = None,
) -> bytes:
    """
    画像を生成してPNGのバイト列を返す（OpenRouter 経由の画像モデル）。

    引数:
        prompt: 生成用のテキストプロンプト。
        size: 画像サイズ（例: "1024x576", "1024x1024"）。未指定時は "1024x576"。
        base_images: 全シーン共通の参照画像（最大5枚）。
        scene_images: 直近シーンの参照画像（最大5枚）。
            いずれも PNG バイト列で、Chat Completions の画像入力として data URL 化して送信。
    戻り値:
        PNG のバイト列。
    """

    s = get_settings()
    # サイズ指定があればプロンプト末尾にフラグ形式で付加
    w, h = _parse_wh(size, "1024x576")
    guidance_parts: list[str] = []
    prompt_with_size = f"{prompt} --width {w} --height {h}"

    combined_images: list[bytes] = []
    if base_images:
        combined_images.extend(base_images)
        guidance_parts.append(
            # 日本語訳: 基本参照画像と一貫性のあるキャラクターのアイデンティティ、衣装、全体的なビジュアルスタイルを維持する。
            "Maintain character identity, costumes, and overarching visual style consistent with the base reference images."
        )
    if scene_images:
        combined_images.extend(scene_images)
        guidance_parts.append(
            # 日本語訳: 直近のシーン参照画像と一貫性を保ちつつ、ポーズ、カメラアングル、背景、照明を変化させた新しい構図を作成する。
            "Ensure continuity with the most recent scene references but craft a new composition with varied pose, camera angle, background, and lighting."
        )

    if combined_images:
        prompt_with_size += " " + " ".join(guidance_parts)

    # 日本語コメント: 参照画像を最大5枚まで組み立て
    content_items: list[dict[str, Any]] = [{"type": "text", "text": prompt_with_size}]
    if combined_images:
        refs: list[bytes] = list(combined_images)[-5:]
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
        if combined_images:
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
        obj: Dict[str, Any]
        if hasattr(resp, "model_dump"):
            obj = cast(Dict[str, Any], resp.model_dump())  # type: ignore[assignment]
        else:  # 予備
            try:
                obj = cast(Dict[str, Any], json.loads(resp.json()))  # type: ignore[attr-defined]
            except Exception:
                obj = cast(Dict[str, Any], json.loads(getattr(resp, "to_json", lambda: "{}")()))

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


def _fetch_bytes(url: str, headers: Dict[str, str] | None = None) -> bytes:
    req = request.Request(url, headers=headers or {}, method="GET")
    with request.urlopen(req) as r:
        return r.read()


def _extract_image_bytes_from_response(obj: Dict[str, Any]) -> Optional[bytes]:
    # いくつかの候補パスを試す
    try:
        # chat.completions 形式
        choices: List[Dict[str, Any]] = cast(List[Dict[str, Any]], obj.get("choices") or [])
        if choices:
            message: Dict[str, Any] = cast(Dict[str, Any], choices[0].get("message") or {})
            if message:
                images: List[Dict[str, Any]] = cast(
                    List[Dict[str, Any]], message.get("images") or [])
                for im in images:
                    b64_val: Optional[str] = None
                    inner_image: Dict[str, Any] = cast(Dict[str, Any], im.get("image") or {})
                    b64_raw: Optional[str] = cast(Optional[str], im.get(
                        "b64_json") or inner_image.get("b64_json"))
                    if isinstance(b64_raw, str):
                        b64_val = b64_raw
                    if b64_val:
                        return base64.b64decode(b64_val)
                    url: Optional[str] = None
                    if isinstance(im.get("image_url"), dict):
                        url = cast(Optional[str], im["image_url"].get("url"))
                    elif isinstance(im.get("image"), dict):
                        url = cast(Optional[str], im["image"].get("url"))
                    if url:
                        return _fetch_bytes(url)
    except Exception:
        return None
    return None
