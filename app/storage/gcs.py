from __future__ import annotations

import base64
import json
from functools import lru_cache
from datetime import timedelta
from typing import Optional

from typing import Any, cast
from google.cloud import storage  # type: ignore
from google.oauth2 import service_account  # type: ignore

from app.config.settings import get_settings


@lru_cache(maxsize=1)
def _client() -> storage.Client:
    """Create a Storage client.

    Prefers explicit credentials from `GCP_SA_KEY_B64` when provided,
    otherwise falls back to Application Default Credentials.
    """
    s = get_settings()
    if s.gcp_sa_key_b64:
        try:
            raw = base64.b64decode(s.gcp_sa_key_b64)
            info = cast(dict[str, Any], json.loads(raw.decode("utf-8")))
            creds = service_account.Credentials.from_service_account_info(info)
            project = cast(str | None, s.gcp_project or info.get("project_id"))
            return storage.Client(project=project, credentials=creds)
        except Exception as e:
            raise RuntimeError("Failed to load GCP service account from GCP_SA_KEY_B64") from e
    # Fallback: ADC (e.g., on Cloud Run or when GOOGLE_APPLICATION_CREDENTIALS is set)
    return storage.Client()


def _bucket(bucket_name: Optional[str] = None) -> storage.Bucket:
    if not bucket_name:
        raise RuntimeError("GCS bucket is required. Pass bucket_name explicitly to storage helpers.")
    return _client().bucket(bucket_name)


def upload_bytes(path: str, data: bytes, content_type: str = "application/octet-stream", bucket_name: Optional[str] = None) -> str:
    b = _bucket(bucket_name)
    blob = b.blob(path)
    blob.upload_from_string(data, content_type=content_type)
    return f"gs://{b.name}/{path}"


def upload_file(path: str, local_file: str, content_type: Optional[str] = None, bucket_name: Optional[str] = None) -> str:
    b = _bucket(bucket_name)
    blob = b.blob(path)
    blob.upload_from_filename(local_file, content_type=content_type)
    return f"gs://{b.name}/{path}"


def signed_url(path: str, expire_seconds: Optional[int] = None, bucket_name: Optional[str] = None) -> str:
    s = get_settings()
    expires = expire_seconds if expire_seconds is not None else s.signed_url_expire_seconds
    b = _bucket(bucket_name)
    blob = b.blob(path)
    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(seconds=expires),
        method="GET",
    )
    return url
