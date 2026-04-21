"""
Send digest emails based on stored subscriber preferences.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from email_sender import EmailSender
from nexttoken_sections import filter_digest_by_sections
from subscription_registry import DEFAULT_REGISTRY_PATH, active_subscriptions
from supabase_subscription_store import load_active_subscriptions_from_supabase


def dispatch_digest_to_subscribers(
    digest: dict[str, Any],
    email_config: dict[str, Any],
    output_dir: str | Path = "output",
    registry_path: str | Path = DEFAULT_REGISTRY_PATH,
    dry_run: bool = False,
) -> dict[str, Any]:
    source = "local"
    try:
        subscribers = load_active_subscriptions_from_supabase()
        source = "supabase"
    except Exception:
        subscribers = active_subscriptions(registry_path)

    if not subscribers:
        return {"used_registry": False, "sent": [], "skipped": [], "source": source}

    sent: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for subscriber in subscribers:
        email = str(subscriber.get("email") or "").strip()
        section_ids = subscriber.get("section_ids") or []
        filtered_digest = filter_digest_by_sections(digest, section_ids)

        if filtered_digest.get("total_count", 0) <= 0:
            skipped.append(
                {
                    "email": email,
                    "reason": "no matching stories",
                    "section_ids": section_ids,
                }
            )
            continue

        sender = EmailSender(dict(email_config))
        ok = sender.send_digest_to_recipient(filtered_digest, email, dry_run=dry_run)
        if ok:
            sent.append({"email": email, "section_ids": section_ids})
        else:
            skipped.append(
                {
                    "email": email,
                    "reason": "send failed",
                    "section_ids": section_ids,
                }
            )

    return {
        "used_registry": True,
        "sent": sent,
        "skipped": skipped,
        "registry_path": str(Path(registry_path)),
        "source": source,
    }
