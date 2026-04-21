#!/usr/bin/env python3
"""
分段采集总控。

将每个平台来源放到独立 Python 子进程里采集，避免浏览器型 crawler 和大规模线程池
在同一个进程内互相影响。所有分段结果最终会合并成一份 raw_items.json，再进入
processing / preview / email。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from crawlers import (  # noqa: E402
    InstagramCrawler,
    ProductHuntCrawler,
    RSSCrawler,
    RedditCrawler,
    SiteCrawler,
    WechatCrawler,
    XCrawler,
    XiaohongshuCrawler,
)
from build_nexttoken_site import build_site_data, write_site_data  # noqa: E402
from email_sender import EmailSender  # noqa: E402
from main import load_config, load_digest, run_processing_pipeline  # noqa: E402
from subscription_dispatch import dispatch_digest_to_subscribers  # noqa: E402


GROUPS = (
    "rss",
    "x",
    "product_hunt",
    "xiaohongshu",
    "site",
    "wechat",
    "instagram",
    "reddit",
)


def _group_output_path(output_dir: Path, group: str) -> Path:
    return output_dir / "groups" / f"{group}.json"


def _serialize_items(items) -> list[dict]:
    return [item.to_dict() for item in items]


def _collect_group(group: str, config) -> list[dict]:
    if group == "rss":
        crawler = RSSCrawler(config.RSS_SOURCES, config.RSS_CRAWLER_CONFIG)
        return _serialize_items(crawler.crawl(hours=config.TIME_RANGE_HOURS))
    if group == "x" and config.X_API_CONFIG.get("enabled"):
        crawler = XCrawler(config.X_API_CONFIG, config.X_SOURCES)
        return _serialize_items(crawler.crawl(hours=config.TIME_RANGE_HOURS))
    if group == "product_hunt" and config.PRODUCT_HUNT_CONFIG.get("enabled"):
        crawler = ProductHuntCrawler(config.PRODUCT_HUNT_CONFIG)
        return _serialize_items(crawler.crawl(hours=config.TIME_RANGE_HOURS))
    if group == "xiaohongshu" and config.XIAOHONGSHU_CONFIG.get("enabled"):
        crawler = XiaohongshuCrawler(config.XIAOHONGSHU_CONFIG, config.XIAOHONGSHU_SOURCES)
        return _serialize_items(crawler.crawl(hours=config.TIME_RANGE_HOURS))
    if group == "site" and config.SITE_CRAWLER_CONFIG.get("enabled"):
        crawler = SiteCrawler(config.SITE_SOURCES, config.SITE_CRAWLER_CONFIG)
        return _serialize_items(crawler.crawl(hours=config.TIME_RANGE_HOURS))
    if group == "wechat" and config.WECHAT_CONFIG.get("enabled"):
        crawler = WechatCrawler(config.WECHAT_CONFIG, config.WECHAT_SOURCES)
        return _serialize_items(crawler.crawl(hours=config.TIME_RANGE_HOURS))
    if group == "instagram" and config.INSTAGRAM_CONFIG.get("enabled"):
        crawler = InstagramCrawler(config.INSTAGRAM_CONFIG, config.INSTAGRAM_SOURCES)
        return _serialize_items(crawler.crawl(hours=config.TIME_RANGE_HOURS))
    if group == "reddit" and config.REDDIT_CONFIG.get("enabled"):
        crawler = RedditCrawler(config.REDDIT_CONFIG, config.REDDIT_SOURCES)
        return _serialize_items(crawler.crawl(hours=config.TIME_RANGE_HOURS))
    return []


def _run_group_mode(group: str) -> None:
    config = load_config()
    output_dir = Path(config.OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = _group_output_path(output_dir, group)
    path.parent.mkdir(parents=True, exist_ok=True)

    items = _collect_group(group, config)
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📦 分段结果已保存: {path} ({len(items)} 条)")


def _run_pipeline_mode(groups: list[str], dry_run: bool, recipient: str | None, digest_date: str | None = None) -> None:
    config = load_config()
    if recipient:
        config.EMAIL_CONFIG["recipient_email"] = recipient

    output_dir = Path(config.OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    for group in groups:
        print(f"\n=== 采集分段: {group} ===")
        subprocess.run(
            [sys.executable, "-u", str(Path(__file__).resolve()), "--group", group],
            check=True,
        )

    merged_items: list[dict] = []
    for group in groups:
        path = _group_output_path(output_dir, group)
        if not path.exists():
            continue
        merged_items.extend(json.loads(path.read_text(encoding="utf-8")))

    raw_items_path = output_dir / "raw_items.json"
    raw_items_path.write_text(
        json.dumps(merged_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\n📦 合并原始条目: {len(merged_items)} 条")
    print(f"📦 合并文件已保存: {raw_items_path}")

    digest_path = run_processing_pipeline(raw_items_path, output_dir, digest_date=digest_date)
    digest = load_digest(digest_path)
    sender = EmailSender(config.EMAIL_CONFIG)
    sender.build_preview_assets(digest, output_dir=output_dir)
    print(f"📰 digest 已生成: {digest_path}")
    print(f"📄 HTML 预览: {output_dir / 'preview.html'}")
    workspace_root = Path(__file__).resolve().parents[3]
    site_data_path = workspace_root / "website" / "data" / "site-data.js"
    site_data = build_site_data(digest_path, archive_dir=workspace_root / "output" / "runs")
    write_site_data(site_data_path, site_data)
    print(f"🌐 网站数据已更新: {site_data_path}")

    if dry_run:
        print("\n✨ Split dry-run 完成")
        return

    dispatch_result = {"used_registry": False}
    if not recipient:
        dispatch_result = dispatch_digest_to_subscribers(
            digest,
            config.EMAIL_CONFIG,
            output_dir=output_dir,
            dry_run=False,
        )
    if dispatch_result.get("used_registry"):
        print(f"\n📬 已按订阅表发送 {len(dispatch_result.get('sent', []))} 封邮件")
    else:
        print(f"\n📬 发送邮件到 {config.EMAIL_CONFIG['recipient_email']} ...")
        sender.send_digest(digest, output_dir=output_dir, dry_run=False)
    print("\n✨ Split pipeline 完成")


def main() -> None:
    parser = argparse.ArgumentParser(description="分段采集 AI 资讯流水线")
    parser.add_argument("--group", choices=GROUPS, help="仅运行单个采集分段")
    parser.add_argument(
        "--groups",
        help="逗号分隔的分段列表，默认全量运行",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅采集和生成预览，不发送邮件")
    parser.add_argument("--recipient", help="覆盖收件人邮箱")
    parser.add_argument("--date", help="日报日期 YYYY-MM-DD；缺省为今天")
    args = parser.parse_args()

    if args.group:
        _run_group_mode(args.group)
        return

    groups = [part.strip() for part in (args.groups or ",".join(GROUPS)).split(",") if part.strip()]
    _run_pipeline_mode(groups, dry_run=args.dry_run, recipient=args.recipient, digest_date=args.date)


if __name__ == "__main__":
    main()
