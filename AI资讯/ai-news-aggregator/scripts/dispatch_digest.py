#!/usr/bin/env python3
"""
Send an existing digest to active subscribers without crawling again.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))

from subscription_dispatch import dispatch_digest_to_subscribers  # noqa: E402


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TIMEZONE = "America/New_York"


def default_digest_date(timezone_name: str = DEFAULT_TIMEZONE) -> str:
    today = datetime.now(ZoneInfo(timezone_name)).date()
    return (today - timedelta(days=1)).isoformat()


def candidate_digest_paths(digest_date: str) -> list[Path]:
    return [
        WORKSPACE_ROOT / "website" / "data" / "digests" / f"digest_{digest_date}.json",
        WORKSPACE_ROOT / "output" / "runs" / digest_date / f"digest_{digest_date}.json",
        WORKSPACE_ROOT / "output" / "runs" / digest_date / "digest.json",
        WORKSPACE_ROOT / "output" / "digest.json",
    ]


def resolve_digest_path(explicit_path: str | None, digest_date: str) -> Path:
    if explicit_path:
        path = Path(explicit_path)
        if not path.is_absolute():
            path = WORKSPACE_ROOT / path
        if not path.exists():
            raise FileNotFoundError(f"Digest not found: {path}")
        return path

    for path in candidate_digest_paths(digest_date):
        if path.exists():
            return path

    candidates = "\n".join(str(path) for path in candidate_digest_paths(digest_date))
    raise FileNotFoundError(f"No digest found for {digest_date}. Checked:\n{candidates}")


def load_digest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_email_config() -> dict:
    return {
        "smtp_server": os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
        "use_tls": os.environ.get("SMTP_USE_TLS", "true").lower() != "false",
        "sender_email": os.environ.get("SMTP_SENDER_EMAIL", ""),
        "sender_password": os.environ.get("SMTP_SENDER_PASSWORD", ""),
        "recipient_email": os.environ.get("SMTP_RECIPIENT_EMAIL", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Dispatch an existing digest to active subscribers")
    parser.add_argument("digest", nargs="?", help="Optional digest JSON path")
    parser.add_argument("--date", help="Digest date YYYY-MM-DD; defaults to yesterday in New York")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-local-registry", action="store_true", help="Allow fallback to data/subscriptions.json")
    args = parser.parse_args()

    digest_date = args.date or default_digest_date(args.timezone)
    digest_path = resolve_digest_path(args.digest, digest_date)
    digest = load_digest(digest_path)

    result = dispatch_digest_to_subscribers(
        digest,
        load_email_config(),
        output_dir=WORKSPACE_ROOT / "output" / "runs" / digest_date,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get("source") != "supabase" and not args.allow_local_registry:
        raise SystemExit("Supabase subscriber registry was not used. Check SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, and SUPABASE_SERVICE_ROLE_KEY.")

    failed = [entry for entry in result.get("skipped", []) if entry.get("reason") == "send failed"]
    if failed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
