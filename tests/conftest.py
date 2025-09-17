from __future__ import annotations

import os
import pytest

from app.utils.env import outputs_root

# .env 読み込み（pytest 実行時）
try:
    from dotenv import load_dotenv, find_dotenv

    _env_path = find_dotenv(filename=".env", raise_error_if_not_found=False, usecwd=True)
    if _env_path:
        load_dotenv(_env_path, override=False)
except Exception:
    pass


def pytest_load_initial_conftests(args, early_config, parser):
    """pytest起動直後に必ず呼ばれるフック。ここでPYTEST=1を設定する。"""
    os.environ["PYTEST"] = "1"


# 念のためデフォルトでも設定（フックが呼ばれない状況の保険）
os.environ.setdefault("PYTEST", "1")


@pytest.fixture(scope="session")
def test_env():
    """
    テスト用フィクスチャ。
    - 必ず環境変数 PYTEST=1 を設定
    - 出力先ディレクトリ（outputs/）を用意し、パスを返す

    実行例:
        pytest -s tests/test_services.py -k "test_split_scenes_real"
    """
    os.environ["PYTEST"] = "1"
    out = outputs_root()
    return {"outputs_dir": out}
