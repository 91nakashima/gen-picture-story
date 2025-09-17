from __future__ import annotations

import base64
import json
from typing import Iterable
from urllib import request, error

from app.config.settings import get_settings
from app.utils.env import env_truthy
from app.utils.log import log


# OpenAI/互換APIの画像サイズでよく使われる値（必要に応じて追加）
_ALLOWED_IMAGE_SIZES: set[str] = {
    "auto",
    "256x256",
    "512x512",
    "1024x1024",
    "1536x1024",
    "1024x1536",
    "1792x1024",
    "1024x1792",
}


def generate_image(
    prompt: str,
    size: str | None = None,
    images: Iterable[bytes | str] | None = None,
) -> bytes:
    """画像を生成してPNGのバイト列を返します（OpenRouter経由でGeminiを利用）。

    引数:
        prompt: 生成用のテキストプロンプト。
        size: 画像サイズ（例: "1024x576", "1024x1024"）。未指定時は設定値。
        images: 参照画像。現時点では未対応。
    戻り値:
        PNG のバイト列。
    """
    if images:
        # 参照画像による生成は現時点では未対応
        raise NotImplementedError("image-to-image は未対応です")

    s = get_settings()
    requested = size or s.default_image_size
    norm_size = requested if requested in _ALLOWED_IMAGE_SIZES else "1024x1024"

    # OpenRouter の Images エンドポイントを叩く
    url = f"{s.openrouter_base_url.rstrip('/')}/images"
    model = s.model_image  # 既定: google/gemini-2.5-flash-image-preview
    payload = {
        "model": model,
        "prompt": prompt,
        "size": norm_size,
        "n": 1,
    }
    data = json.dumps(payload).encode("utf-8")

    # APIキーは AAP_OPENROUTER_API_KEY 優先、なければ OPENROUTER_API_KEY
    api_key = s.aap_openrouter_api_key or s.openrouter_api_key
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY または AAP_OPENROUTER_API_KEY が未設定です")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    # 推奨ヘッダがあれば付与
    if s.openrouter_site_url:
        headers["HTTP-Referer"] = s.openrouter_site_url
    if s.openrouter_app_title:
        headers["X-Title"] = s.openrouter_app_title

    req = request.Request(url, method="POST", headers=headers, data=data)
    try:
        with request.urlopen(req) as resp:
            body = resp.read()
    except error.HTTPError as e:
        msg = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenRouter image API error: {e.code} {msg}") from e
    except error.URLError as e:
        raise RuntimeError(f"OpenRouter image API connection error: {e}") from e

    try:
        obj = json.loads(body.decode("utf-8"))
    except Exception as e:
        raise RuntimeError("OpenRouter image API が不正なJSONを返しました") from e

    arr = obj.get("data") or []
    if not arr or not isinstance(arr, list):
        raise RuntimeError("画像生成の結果データが空です")
    b64 = arr[0].get("b64_json")
    if not isinstance(b64, str):
        raise RuntimeError("画像生成の応答に base64 データが含まれていません")

    png = base64.b64decode(b64)
    if env_truthy("PYTEST", "0"):
        log("[generate_image] size=", norm_size)
        log("[generate_image] prompt=\n", prompt)
    return png
