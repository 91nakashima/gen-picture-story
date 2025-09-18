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


# コメントについて
コメントは、日本語で記載してください。
## 例
```
def split_scenes(text: str, max_scenes: int = 5) -> List[str]:
    """
    LLMを用いて物語テキストを最大N個のシーンへ分割する。

    Params:
        text: 物語テキスト（日本語）
        max_scenes: 分割するシーンの最大数
    Returns:
        シーンのリスト（空でないことを保証）
    """
    ...
```