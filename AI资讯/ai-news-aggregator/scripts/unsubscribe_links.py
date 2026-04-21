"""
Build signed unsubscribe links for subscriber emails.
"""
from __future__ import annotations

import hmac
import os
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SITE_BASE_URL = "https://ai-news-site.haolin-wang819.workers.dev"


def _load_root_env_file() -> None:
    env_path = WORKSPACE_ROOT / ".env.local"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _normalized_email(email: str) -> str:
    return str(email or "").strip().lower()


def site_base_url(config: dict | None = None) -> str:
    _load_root_env_file()
    configured = ""
    if config:
        configured = str(config.get("site_base_url") or config.get("public_site_url") or "").strip()
    value = configured or os.environ.get("NEXTTOKEN_SITE_URL") or os.environ.get("PUBLIC_SITE_URL") or DEFAULT_SITE_BASE_URL
    return str(value).strip().rstrip("/")


def unsubscribe_secret() -> str:
    _load_root_env_file()
    return str(os.environ.get("UNSUBSCRIBE_SECRET") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()


def unsubscribe_token(email: str) -> str:
    secret = unsubscribe_secret()
    if not secret:
        raise ValueError("UNSUBSCRIBE_SECRET or SUPABASE_SERVICE_ROLE_KEY is required to sign unsubscribe links")

    normalized = _normalized_email(email)
    return hmac.new(secret.encode("utf-8"), normalized.encode("utf-8"), sha256).hexdigest()


def build_unsubscribe_url(email: str, config: dict | None = None) -> str:
    normalized = _normalized_email(email)
    query = urlencode(
        {
            "email": normalized,
            "token": unsubscribe_token(normalized),
        }
    )
    return f"{site_base_url(config)}/api/unsubscribe?{query}"
