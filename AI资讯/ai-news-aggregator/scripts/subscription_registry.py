"""
Subscriber registry persistence helpers.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nexttoken_sections import normalize_section_ids, section_labels


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_PATH = WORKSPACE_ROOT / "data" / "subscriptions.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def load_registry(path: str | Path = DEFAULT_REGISTRY_PATH) -> dict[str, Any]:
    registry_path = Path(path)
    if not registry_path.exists():
        return {"subscribers": []}

    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"subscribers": []}

    subscribers = payload.get("subscribers")
    if not isinstance(subscribers, list):
        subscribers = []
    return {"subscribers": subscribers}


def save_registry(payload: dict[str, Any], path: str | Path = DEFAULT_REGISTRY_PATH) -> Path:
    registry_path = Path(path)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return registry_path


def upsert_subscription(
    email: str,
    modules: list[str] | tuple[str, ...] | None,
    path: str | Path = DEFAULT_REGISTRY_PATH,
    source: str = "website",
) -> dict[str, Any]:
    normalized_email = _normalize_email(email)
    if not normalized_email or "@" not in normalized_email:
        raise ValueError("Invalid subscriber email")

    section_ids = normalize_section_ids(list(modules or []))
    now = _now_iso()
    registry = load_registry(path)
    subscribers = registry["subscribers"]

    existing = None
    for subscriber in subscribers:
        if _normalize_email(subscriber.get("email", "")) == normalized_email:
            existing = subscriber
            break

    record = {
        "email": normalized_email,
        "status": "active",
        "section_ids": section_ids,
        "section_labels": section_labels(section_ids),
        "source": source,
        "updated_at": now,
    }

    if existing:
        record["created_at"] = existing.get("created_at") or now
        existing.update(record)
    else:
        record["created_at"] = now
        subscribers.append(record)

    save_registry(registry, path)
    return record


def active_subscriptions(path: str | Path = DEFAULT_REGISTRY_PATH) -> list[dict[str, Any]]:
    registry = load_registry(path)
    return [
        subscriber
        for subscriber in registry["subscribers"]
        if str(subscriber.get("status") or "active").lower() != "inactive"
    ]
