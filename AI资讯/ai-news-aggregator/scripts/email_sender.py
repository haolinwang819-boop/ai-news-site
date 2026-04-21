"""
邮件发送模块。

基于 digest 产物发送邮件，并复用 display 层生成的 Markdown / HTML 预览。
"""
from __future__ import annotations

import smtplib
from datetime import datetime
from email.utils import getaddresses
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from render_digest_preview import render_assets, render_email_html, render_email_markdown


class EmailSender:
    """digest 驱动的邮件发送器。"""

    def __init__(self, config: dict):
        self.config = config

    def send_digest(self, digest: dict, output_dir: str | Path = "output", dry_run: bool = False) -> bool:
        output_path = Path(output_dir)
        assets = render_assets(digest, output_path)

        if dry_run:
            print(f"\n📄 网页 Markdown 预览: {assets['web_md']}")
            print(f"📄 邮件 Markdown 预览: {assets['email_md']}")
            print(f"📄 HTML 预览: {assets['html']}")
            return True

        try:
            markdown_text = assets["email_md"].read_text(encoding="utf-8")
            html_content = assets["html"].read_text(encoding="utf-8")
            return self._send_email_content(digest, html_content, markdown_text)
        except Exception as e:
            print(f"\n❌ 邮件发送失败: {e}")
            return False

    def send_digest_to_recipient(self, digest: dict, recipient_email: str, dry_run: bool = False) -> bool:
        markdown_text = render_email_markdown(digest)
        html_content = render_email_html(digest)

        if dry_run:
            print(f"\n📄 预演发送到 {recipient_email}")
            print(f"📄 HTML 长度: {len(html_content)}")
            print(f"📄 Markdown 长度: {len(markdown_text)}")
            return True

        try:
            return self._send_email_content(digest, html_content, markdown_text, recipients=[recipient_email])
        except Exception as e:
            print(f"\n❌ 邮件发送失败: {e}")
            return False

    def _subject_for_digest(self, digest: dict) -> str:
        top_title = "Daily AI Brief"
        for category in ("breakout_products", "hot_news", "llm", "image_video", "product_updates"):
            items = digest.get("categories", {}).get(category) or []
            if items:
                top_title = items[0].get("display_title") or items[0].get("title") or top_title
                break
        return f"[Daily AI Brief] {digest.get('date', datetime.now().strftime('%Y-%m-%d'))} — {top_title}"

    def _send_email_content(
        self,
        digest: dict,
        html_content: str,
        markdown_text: str,
        recipients: list[str] | None = None,
    ) -> bool:
        recipients = recipients or self._parse_recipients(self.config["recipient_email"])
        if not recipients:
            raise ValueError("未配置有效收件人邮箱")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = self._subject_for_digest(digest)
        msg["From"] = self.config["sender_email"]
        msg["To"] = ", ".join(recipients)

        msg.attach(MIMEText(markdown_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        with smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"]) as server:
            if self.config.get("use_tls", True):
                server.starttls()
            server.login(self.config["sender_email"], self.config["sender_password"])
            server.send_message(msg, to_addrs=recipients)

        print(f"\n✅ 邮件已发送至 {', '.join(recipients)}")
        return True

    def build_preview_assets(self, digest: dict, output_dir: str | Path = "output") -> dict[str, Path]:
        return render_assets(digest, Path(output_dir))

    def _parse_recipients(self, raw_recipients: str) -> list[str]:
        normalized = raw_recipients.replace(";", ",")
        parsed = [email.strip() for _, email in getaddresses([normalized]) if email.strip()]
        return parsed
