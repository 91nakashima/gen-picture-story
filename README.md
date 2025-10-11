Gen Picture Story (MVP)

概要
- Gradio の Web UI から、OpenAI（LLM/TTS）と OpenRouter 経由の Gemini（画像）を使って 1 シーンの画像と音声を生成し、FFmpeg で MP4 に合成。成果物は GCS に保存し、署名付きURLで返却します。

ローカル実行
1) 依存インストール
```
pip install -r requirements.txt
```
2) 環境変数
```
export OPENAI_API_KEY=sk-...
# 画像生成用（OpenRouter）
export OPENROUTER_API_KEY=or-...
# GCP 認証（サービスアカウントJSONをBase64化して渡す）
# macOS 例: base64 -i service-account.json | tr -d '\n'
export GCP_SA_KEY_B64=eyJ0eXAiOiJKV1QiLCJ...
# 任意: プロジェクトIDを明示したい場合
export GCP_PROJECT=your-project-id
```
3) 起動
```
python -m app.main
```
4) ブラウザ
- http://127.0.0.1:8080

環境変数の読み込み（.env 対応）
- プロジェクト直下の `.env` をアプリ起動時に自動読み込みします（`app/__init__.py`）。
- `pytest` 実行時も `.env` を自動読み込みします（`conftest.py`）。
- 例: `.env`
  ```
  OPENAI_API_KEY=sk-...
  GCP_SA_KEY_B64=...
  GCP_PROJECT=your-project-id
  ```
  そのまま `python -m app.main` / `pytest` で反映されます。


型チェック（Pyright）
- VS Code: 拡張機能に「Pyright」を推奨します（`.vscode/extensions.json`）。
- CLI 実行例:
  - Node: `npx -y pyright`
  - Python venv: `source .venv/bin/activate && pyright`
  - 単一ファイル: `pyright app/services/image_service.py`


Gradio の共有リンク（frpc）について
- 既定では `share=False` 相当で起動します（`GRADIO_SHARE=0`）。
- 共有リンク（`share=True`）は Hugging Face の frpc バイナリをダウンロードします。ネットワーク/セキュリティで遮断される環境では以下のエラーが出ます：
  - `Could not create share link. Missing file: ~/.cache/huggingface/gradio/frpc/...`
- 回避方法:
  - 共有を使わない: そのまま `http://127.0.0.1:8080` にアクセス。
  - どうしても共有したい場合のみ、`GRADIO_SHARE=1` を指定して起動し、必要に応じて frpc を手動配置してください（Gradio の案内に従ってダウンロード→リネーム→所定ディレクトリへ配置）。


Cloud Run デプロイ（Cloud Build）
- `infra/cloudbuild.yaml` を使用し、Artifact Registry へビルド＆デプロイします。
- 必要に応じて substitutions の `_REGION`, `_SERVICE`, `_REPO` を編集してください。

環境変数（主要）
- `OPENAI_API_KEY`（必須・LLM/TTS）
- `OPENROUTER_API_KEY` または `AAP_OPENROUTER_API_KEY`（必須・画像生成）
- `OPENAI_BASE_URL`（任意・エンドポイント切替）
- `GCP_SA_KEY_B64`（推奨・サービスアカウントJSONのBase64。未設定時はADCを利用）
- `GCP_PROJECT`（任意・プロジェクトIDを明示したい場合）
- `MODEL_LLM`（既定: gpt-4o-mini）
- `MODEL_IMAGE`（既定: google/gemini-2.5-flash-image-preview）
- `MODEL_TTS`（既定: gpt-4o-mini-tts）
- `GRADIO_SHARE`（既定: 0／共有リンク無効。1 で有効）
- `GRADIO_PREVENT_THREAD_LOCK`（既定: 0／CLI 実行時にプロセスをブロック。1 で非ブロッキング起動）

テスト実行（統合テスト・実サービス利用）
- このリポジトリのテストはモックを使わず、実際にOpenAI APIやFFmpegを使用します。
- 事前準備:
  - `pip install -r requirements/dev.txt`
  - `AAP_OPENAI_API_KEY` を `.env` もしくは環境変数で設定
  - FFmpeg バイナリをインストール（例: `brew install ffmpeg`）
- 実行例:
  - サービス層のテスト: `pytest -s tests/test_services.py -k "test_generate_image_real"`
  - パイプラインのテスト: `pytest -s tests/test_pipelines.py -k "test_process_scene_local_outputs"`
- 出力先:
  - テスト時（`PYTEST=1`）はリポジトリ直下に `outputs/` ディレクトリを作成し、
    画像・音声・動画を保存します。
- ログ出力:
  - テスト時は `PYTEST=1` が自動で設定され、プロンプトや生成情報が標準出力に出ます。

プロンプトのカスタマイズ（Python関数）
- `prompts/` はPythonモジュールで、以下の関数がシステムプロンプトを返します。
  - `prompts.split_scenes_system()`
  - `prompts.image_prompt_system()`
- これらの関数を編集することで、アシスタントの設定（システムプロンプト）を簡単に調整できます。

注意
- MVP は最初の 1 シーンのみを処理します（複数シーンや連結動画は今後対応）。
- Cloud Run では処理中の待ち時間が長い場合があるため、需要に応じて非同期化（Cloud Run Jobs / Cloud Tasks + Pub/Sub）を検討してください。
