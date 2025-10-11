from __future__ import annotations

import os
from pathlib import Path


def env_truthy(name: str, default: str = "0") -> bool:
    val = os.getenv(name, default)
    if val is None:
        return False
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def outputs_root() -> Path:
    """Return base output directory.

    - When running tests (PYTEST=1), use ./outputs in the repo.
    - Otherwise, use /tmp/projects (existing default behavior base).
    """
    # if env_truthy("PYTEST", "0"):
    #     p = Path("./outputs").resolve()
    #     p.mkdir(parents=True, exist_ok=True)
    #     return p
    # return Path("/tmp") / "projects"
    p = Path("./outputs").resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p
