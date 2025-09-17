プロジェクト仕様: 画像生成 + 音声生成 → 動画化（Python Web UI）

概要
- 目的: テキストから「絵（シーン）」と「ナレーション音声」を生成し、最終的に動画として出力する。
- アプローチ: Python 製の Web UI からワンストップで、プロンプト→画像→音声→動画のパイプラインを実行。
- 方針: 画像・音声・LLM は OpenAI を利用。公開先は GCP Cloud Run、生成物は Google Cloud Storage(GCS) に保存（開発はローカルでも実行可）。

全体フロー（パイプライン）
1) 入力
   - 物語のテキスト（シーンごとに分割済み or UI 上で分割）
   - スタイル指定（例: 絵本風/アニメ風/写実風、キャラ設定、色味など）
   - 音声指定（声の種類、速度、高さ、BGM 有無）
2) 画像生成（シーンごと）
   - 指定プロンプトから 1〜数枚を生成 → ベストショット選択
   - キャラ一貫性のためにシード固定や LoRA 等の追加も可
3) 音声生成（シーンごと）
   - ナレーション TTS を生成（日本語対応）
   - BGM/効果音のミックス（任意）
4) 動画合成
   - 画像をスライド化（Ken Burns エフェクト等の簡易アニメーション）
   - シーン音声に合わせて尺合わせ、トランジション追加
   - 字幕焼き込み or SRT 併出力（任意）
5) 出力
   - MP4（H.264/AAC）を標準出力形式に
   - 画像（PNG/JPG）、音声（WAV/MP3）、字幕（SRT）、プロジェクト設定（JSON/YAML）を保存

技術選定

Web UI
- Gradio（推奨・最小実装向き）
  - 理由: 実装が容易、Python 単体で完結、ファイル入出力に強い
- 代替: Streamlit / FastAPI + 前段（Gradio or React）

画像生成
- OpenAI Images API（`gpt-image-1` など）
  - 特徴: 高品質な画像生成とバリアント/編集に対応、エッジケースの扱いが安定
  - 実装: OpenAI Python SDK の `images.generate` を使用

音声生成（TTS）
- OpenAI TTS（例: `gpt-4o-mini-tts` など）
  - 特徴: 高品質な日本語 TTS、複数ボイス
  - 実装: OpenAI Python SDK の TTS エンドポイントを使用

LLM（テキスト処理）
- OpenAI Responses/Chat Completions（例: `gpt-4o-mini`）
  - 用途: シーン分割、画像プロンプト生成、字幕文生成、BGM 指示、メタデータ作成 等
  - 実装: OpenAI Python SDK の `responses` or `chat.completions` を使用

動画合成
- FFmpeg（外部バイナリ） + Python ラッパ（`ffmpeg-python`）
  - 長所: 高速・高品質、細かいエフェクト制御、エンコード安定
- 代替: MoviePy（純 Python で簡単、ただしパフォーマンスは FFmpeg 直叩きに劣る）

字幕/テキスト
- 生成済みテキストから SRT/VTT を出力
- 字幕焼き込みは FFmpeg フィルタ（`subtitles`, `drawtext`）で対応

設定/プロジェクト管理
- 設定は `.yaml` or `.json` で保存（再現性確保）
- 一時生成物と成果物を以下のように整理
  - `projects/<name>/config.yaml`
  - `projects/<name>/scenes/<idx>/image.png`
  - `projects/<name>/scenes/<idx>/narration.wav`
  - `projects/<name>/final/<name>.mp4`

仕様詳細

入力
- シーン分割方法
  - 手動: UI で段落ごとに入力/編集
  - 半自動: 記号（句点、改行）で分割 → UI で微調整
- 画像プロンプト
  - 全体プリセット + シーン固有の追加プロンプト
  - ネガティブプロンプト対応
- 音声プロンプト
  - ナレーションテキスト、話者、速度、ピッチ、感情（対応エンジンのみ）

画像生成
- 既定値（例）
  - 解像度: 1024x576（16:9）/ 1024x1024（正方）
  - ステップ数: 25–50
  - ガイダンススケール: 5–8
  - シード: 自動 or 固定（キャラ一貫性用）
  - LoRA: 任意（キャラ/スタイル強化）
- 生成枚数と選別
  - シーンあたり 1–3 枚を生成 → UI で選択採用

音声生成
- 出力形式: WAV（内部処理）→ MP3/AAC に変換可
- 話者: VOICEVOX の話者 ID / Piper モデル選択
- パラメータ: 速度、ピッチ、感情（エンジン依存）
- BGM/SE: 任意でミックス（`pydub` など）

動画生成
- 出力形式: MP4（H.264 + AAC）
- 解像度/FPS: 1920x1080 30fps（既定、可変）
- 画像配置: 全画面 or 余白付与（`scale`/`pad`）
- アニメーション: Ken Burns（`zoom/pan`）を軽く付与（任意）
- トランジション: `crossfade`/`fade`（任意、0.3–0.6s）
- 字幕: SRT を別出力、焼き込みは任意

Web UI（初期画面案）
- プロジェクト作成/読込
- 物語テキスト入力 → シーン分割プレビュー
- スタイル/モデル選択（画像）
- 話者/声質選択（音声）
- シーンごとのプレビュー（画像再生成、音声再生成）
- 動画設定（解像度/FPS/トランジション/字幕）
- 実行ボタン（全自動生成）/ 途中再開
- 生成結果ダウンロード（MP4, SRT, 素材一式）

依存関係（最小構成）
- Python 3.10+
- OpenAI SDK: `openai`（v1 系）
- Web UI: `gradio`
- 動画: `ffmpeg`（外部バイナリ必須） + `ffmpeg-python` or `moviepy`
- 画像/音声処理: `Pillow`, `numpy`, `pydub`（任意）
- GCP SDK: `google-cloud-storage`（GCS 連携）
- ユーティリティ: `python-dotenv`（任意）、`tenacity`（リトライ任意）

環境メモ
- すべて OpenAI API 経由のため GPU は不要（Cloud Run CPU で運用）
- FFmpeg のみ外部バイナリで必要

ライセンス/モデル取り扱い
- 利用するモデル（SD/LoRA/TTS）のライセンス順守（商用可否、クレジット表記など）
- BGM/SE の著作権に注意（自作 or ライセンス明確な素材を使用）

フォルダ構成（例）
```
.
├─ app/
│  ├─ main.py                 # Gradio 起動（PORT=8080）
│  ├─ ui/
│  │  └─ gradio_ui.py        # 画面構成、イベントハンドラ
│  ├─ services/
│  │  ├─ image_service.py    # 画像生成（OpenRouter 経由の Gemini）
│  │  ├─ tts_service.py      # TTS（OpenAI TTS）
│  │  └─ llm_service.py      # LLM（シーン分割/プロンプト生成 等）
│  ├─ pipelines/
│  │  ├─ generate_scene.py   # シーン単位の画像+音声生成
│  │  └─ compose_video.py    # FFmpeg で動画合成
│  ├─ storage/
│  │  └─ gcs.py              # GCS アップロード/署名付き URL
│  └─ config/
│     └─ settings.py         # 環境変数管理（pydantic/自作）
├─ infra/
│  ├─ Dockerfile             # Cloud Run 用（ffmpeg インストール）
│  ├─ cloudbuild.yaml        # CI/CD（Artifact Registry へ push → deploy）
│  └─ run_local.sh           # ローカル起動補助（任意）
├─ requirements/
│  ├─ base.txt               # ランタイム依存（pin）
│  ├─ prod.txt               # 本番用（= base）
│  └─ dev.txt                # 開発用（lint/test 追加）
├─ requirements.txt          # `-r requirements/prod.txt`（Cloud Run が参照）
└─ docs/
   └─ DOCS.md
```

保存先ポリシー
- 実行時一時ファイルは `/tmp/<project>/<scene>/...` に作成し、完了後すぐに GCS へアップロード
- GCS パス例: `gs://<project-id>-story/projects/<name>/scenes/<idx>/image.png` など

GCP デプロイ構成（Cloud Run + GCS）
- サービス構成
  - Cloud Run: Python Web UI（Gradio）。HTTP 受け付け（ポート `8080`）。
  - Google Cloud Storage: 画像・音声・動画の恒久保存先。
- 画像/TTS/LLM は OpenAI API を使用（外部通信が必要）

- 非同期実行（推奨）
  - UI はジョブ作成 → 即応答。重い処理（画像生成/動画合成）は非同期ワーカーへ。
  - Cloud Run Jobs もしくは Cloud Tasks + Pub/Sub + ワーカー用 Cloud Run で非同期実行。
  - 進捗は GCS 上の `status.json`（または Firestore）をポーリングして表示。

- ストレージ設計
  - バケット例: `gs://<project-id>-story/`
  - パス例: `gs://<project-id>-story/projects/<name>/scenes/<idx>/image.png`, `.../narration.wav`, `.../final/video.mp4`
  - 配布: 署名付き URL（Signed URL）でダウンロード/プレビューを提供（公開不要）。

- IAM/セキュリティ
  - Cloud Run サービスアカウントに `Storage Object Admin`（最小権限なら `Creator` + `Viewer`）
  - API キーは Secret Manager に格納し、環境変数へ注入（`AAP_OPENAI_API_KEY`）
  - GCP TTS 使用時は `Text-to-Speech User` を付与
  - バケットは非公開。アクセスは Signed URL 経由

- Cloud Run 設定の目安
  - メモリ: 1–4 GiB（FFmpeg/画像サイズに応じ調整）
  - CPU: 1–2 vCPU（動画合成の安定性向上で増やす）
  - タイムアウト: 上限（最大 60 分程度）
  - Concurrency: 1–2（FFmpeg の負荷を抑制）
  - Min instances: 0–1（コストと起動時間のバランス）
  - ファイルシステム: `/tmp`（永続化なし）。成果物は完了次第 GCS に即アップロード

- ネットワーク/リージョン
  - Cloud Run / GCS /（GPU や Vertex AI を使う場合は）同一リージョンを推奨
  - egress を最小化して転送コスト削減

- CI/CD
  - Artifact Registry にコンテナを push
  - Cloud Build でビルド/デプロイ（`cloudbuild.yaml`）

環境変数（例）
- `AAP_OPENAI_API_KEY`: OpenAI API Key（Secret Manager から供給）
- `OPENAI_BASE_URL`: エンドポイント切替用（既定: `https://api.openai.com/v1`）
- `OPENAI_ORG` / `OPENAI_PROJECT`: 必要に応じて
- `GCP_SA_KEY_B64`: サービスアカウントJSONのBase64（未設定時はADC使用）
- `GCP_PROJECT`: プロジェクトID（任意）
- `MODEL_LLM`: 既定 `gpt-4o-mini`
- `MODEL_IMAGE`: 既定 `gpt-image-1`
- `MODEL_TTS`: 既定 `gpt-4o-mini-tts`

開発ロードマップ（初期）
1) 最小 MVP
   - Gradio UI: シーン入力 → 1 画像 + 1 音声 → MP4 出力
   - GCS への成果物保存（画像/音声/動画）
   - OpenAI（LLM/画像/TTS）+ FFmpeg 連携
2) 品質向上
   - 複数生成からの選別、Ken Burns、字幕、BGM
   - キャラ一貫性（シード/LoRA）
3) 運用強化
   - 設定の保存/復元、再実行、ログ
   - Cloud Run Jobs / Cloud Tasks 化、進捗 API、署名付き URL 配布
   - エンドポイント切替（`OPENAI_BASE_URL`）で将来の他プロバイダにも対応

未確定事項（要確認）
- 画像の作風/プロンプト方針
  - 絵本風/アニメ風/リアル調の既定スタイル、ネガティブプロンプトの方針
- OpenAI モデルの既定
  - LLM: `gpt-4o-mini` で良いか、他希望はあるか
  - 画像: `gpt-image-1` の出力サイズ/画角（16:9/1:1/9:16）
  - TTS: `gpt-4o-mini-tts` のボイス（例: `alloy`）や話速・音量の既定
- 動画仕様
  - 画角（16:9 / 9:16 / 1:1）、解像度、FPS、トランジション有無
- 字幕
  - 焼き込み or 別ファイル（SRT）で配布
- CI/CD
  - Cloud Build / Artifact Registry の利用可否、デプロイフローの希望

インストール/実行（たたき台）
- 前提: `ffmpeg` をインストール済み
- Python 依存関係（例）
```
pip install -r requirements.txt
```
- OpenAI の利用
  - 環境変数 `AAP_OPENAI_API_KEY` を設定（Secret Manager 推奨）
  - 必要に応じて `OPENAI_BASE_URL` を上書き（エンドポイント切替用）

Cloud Run デプロイ（概要）
- ビルド: Artifact Registry に push（Cloud Build 推奨）
- デプロイ: `--port 8080`、環境変数 `AAP_OPENAI_API_KEY`, `GCP_SA_KEY_B64` 等を設定
- 権限: サービスアカウントに GCS と（必要なら）TTS の権限を付与
- ドメイン: 必要に応じて Cloud Run カスタムドメインを割当

備考
- 実装は「最小構成でまず動かす」→「品質/操作性を段階的に向上」の順で進めます。
- コスト管理のため、画像サイズや連続生成回数、TTS 長さにクォータを設定します。

OpenAI 呼び出し（最小サンプル・擬似コード）
```
from openai import OpenAI
import base64

client = OpenAI(
    api_key=os.environ["AAP_OPENAI_API_KEY"],
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
)

# LLM（シーン分割など）
resp = client.chat.completions.create(
    model=os.getenv("MODEL_LLM", "gpt-4o-mini"),
    messages=[{"role": "user", "content": "<物語テキスト> をシーンに分割して"}],
)
scenes = resp.choices[0].message.content

# 画像生成
img = client.images.generate(
    model=os.getenv("MODEL_IMAGE", "gpt-image-1"),
    prompt="絵本風で...",
    size="1024x576",
)
image_b64 = img.data[0].b64_json
image_bytes = base64.b64decode(image_b64)

# TTS
speech = client.audio.speech.create(
    model=os.getenv("MODEL_TTS", "gpt-4o-mini-tts"),
    voice="alloy",
    input="ナレーションテキスト",
    format="mp3",
)
audio_bytes = speech.read()  # SDK により取得方法は変わる場合あり
```
