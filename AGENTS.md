# コードの変更を行った場合
コードの変更を行った場合は、以下のコマンドを実行してください。
1. 仮想環境アクティベート
  ```bash
  source .venv/bin/activate
  ```
2. 依存関係の更新
  ```bash
  ruff fix .
  pyright .
  ```

# テストについて
テストなどを実行する場合は、以下のコマンドを実行してください。
pytestは、そのファイルのテストしたい関数を指定して、実行してください。

1. 仮想環境アクティベート
  ```bash
  source .venv/bin/activate
  ```
2. テスト実行のサンプルコマンド
  ```bash
  pytest -s tests/test_ファイル名.py -k "テストしたい関数名"
  ```
