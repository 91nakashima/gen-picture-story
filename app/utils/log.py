from __future__ import annotations

import sys
from datetime import datetime

from typing import Any
from app.utils.env import env_truthy


def log(*args: Any, **kwargs: Any) -> None:
    """Print logs when PYTEST or DEBUG is truthy.

    Keeps production quiet by default.
    """
    if env_truthy("PYTEST", "0") or env_truthy("DEBUG", "0"):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}]", *args, **kwargs, file=sys.stdout, flush=True)
