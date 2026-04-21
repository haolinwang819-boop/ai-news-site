"""
Supabase-backed subscription helpers.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


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


def _normalized_url(url: str | None) -> str:
    value = str(url or "").strip().rstrip("/")
    return value


def _rest_endpoint(url: str) -> str:
    return f"{url}/rest/v1/subscriptions"


def supabase_public_config() -> dict[str, str]:
    _load_root_env_file()
    url = _normalized_url(os.environ.get("SUPABASE_URL"))
    publishable_key = str(os.environ.get("SUPABASE_PUBLISHABLE_KEY") or "").strip()
    if not url or not publishable_key:
        return {}
    return {
        "url": url,
        "publishable_key": publishable_key,
    }


def supabase_server_config() -> dict[str, str]:
    public = supabase_public_config()
    service_role_key = str(os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if public and service_role_key:
        return {
            "url": public["url"],
            "service_role_key": service_role_key,
        }
    return {}


def upsert_subscription_to_supabase(record: dict[str, Any], use_service_role: bool = False) -> None:
    config = supabase_server_config() if use_service_role else supabase_public_config()
    if not config:
        raise ValueError("Supabase config is not set")

    key_name = "service_role_key" if use_service_role else "publishable_key"
    key = config[key_name]

    response = requests.post(
        f"{_rest_endpoint(config['url'])}?on_conflict=email",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        json=record,
        timeout=20,
    )
    response.raise_for_status()


def load_active_subscriptions_from_supabase() -> list[dict[str, Any]]:
    config = supabase_server_config()
    if not config:
        raise ValueError("Supabase server config is not set")

    response = requests.get(
        f"{_rest_endpoint(config['url'])}?select=email,status,section_ids,section_labels,source,created_at,updated_at&status=eq.active&order=created_at.asc",
        headers={
            "apikey": config["service_role_key"],
            "Authorization": f"Bearer {config['service_role_key']}",
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []
