from __future__ import annotations

try:
    # Load .env as early as possible so Settings picks them up
    from dotenv import load_dotenv, find_dotenv

    # Search from package location upward; load if found
    _env_path = find_dotenv(filename=".env", raise_error_if_not_found=False, usecwd=False)
    if _env_path:
        load_dotenv(_env_path, override=False)
except Exception:
    # Do not hard-fail if python-dotenv is unavailable at runtime
    pass

__all__ = []
