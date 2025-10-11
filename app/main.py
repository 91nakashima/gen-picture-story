from __future__ import annotations

import os

from app.ui.gradio_ui import build_ui
from app.utils.env import env_truthy


def main():
    port = int(os.getenv("PORT", "8080"))
    # Disable Gradio share tunnel by default to avoid frpc download.
    # Enable only if explicitly requested via env var.
    share = env_truthy("GRADIO_SHARE", "0")
    demo = build_ui()
    # Use queue to limit concurrency for heavy tasks
    prevent_thread_lock = env_truthy("GRADIO_PREVENT_THREAD_LOCK", "0")
    demo.queue(max_size=16).launch(
        server_name="0.0.0.0",
        server_port=port,
        show_api=False,
        # 日本語コメント: デフォルトではプロセスをブロックさせるため False を設定し、必要に応じて環境変数で切り替え可能
        prevent_thread_lock=prevent_thread_lock,
        share=share,
    )


if __name__ == "__main__":
    main()
