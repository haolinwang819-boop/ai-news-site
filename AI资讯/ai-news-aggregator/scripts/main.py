#!/usr/bin/env python3
"""
AI资讯采集器 - 主调度脚本

用法:
    python main.py              # 完整采集流程
    python main.py --dry-run    # 仅采集和处理，不发送邮件
    python main.py --test-email # 发送测试邮件
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from crawlers import (
    InstagramCrawler,
    ProductHuntCrawler,
    RSSCrawler,
    RedditCrawler,
    SiteCrawler,
    WechatCrawler,
    XCrawler,
    XiaohongshuCrawler,
)
from build_nexttoken_site import build_site_data, write_site_data
from email_sender import EmailSender
from subscription_dispatch import dispatch_digest_to_subscribers


def load_config():
    """加载配置"""
    try:
        import config
        return config
    except ImportError:
        print("❌ 配置文件不存在！")
        print("请复制 config_template.py 为 config.py 并填入配置")
        sys.exit(1)


def run_processing_pipeline(raw_items_path: Path, output_dir: Path) -> Path:
    """调用 ai-news-processing 的规范流水线，生成 digest JSON。"""
    processing_root = Path(__file__).resolve().parents[2] / "ai-news-processing"
    runner_path = processing_root / "run.py"
    digest_path = output_dir / "digest.json"

    result = subprocess.run(
        [sys.executable, str(runner_path), str(raw_items_path), "-o", str(digest_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return digest_path


def load_digest(digest_path: Path) -> dict:
    return json.loads(digest_path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="AI资讯采集器")
    parser.add_argument("--dry-run", action="store_true", help="仅采集处理，不发送邮件")
    parser.add_argument("--test-email", action="store_true", help="发送测试邮件")
    parser.add_argument("--sources", help="逗号分隔采集源：rss,x,product_hunt,site,xiaohongshu,wechat,instagram,reddit")
    args = parser.parse_args()
    
    print("=" * 50)
    print("🤖 AI资讯采集器")
    print("=" * 50)
    
    # 加载配置
    config = load_config()
    counts = getattr(config, "NEXTTOKEN_SOURCE_COUNTS", {})
    if counts:
        summary = ", ".join(f"{name}={count}" for name, count in counts.items())
        print(f"📚 Nexttoken来源清单: {summary}")
    
    # 测试邮件模式
    if args.test_email:
        print("\n📧 发送测试邮件...")
        sender = EmailSender(config.EMAIL_CONFIG)
        digest_path = Path(config.OUTPUT_DIR) / "digest.json"
        if not digest_path.exists():
            print("❌ 未找到现有 digest，请先运行一次采集流程")
            return
        sender.send_digest(load_digest(digest_path), output_dir=config.OUTPUT_DIR, dry_run=False)
        return
    
    # 1. 采集
    print("\n📡 开始采集资讯...")
    print("-" * 50)
    
    all_items = []
    selected_sources = {
        name.strip().lower() for name in (args.sources or "rss,x,product_hunt,site,xiaohongshu,wechat,instagram,reddit").split(",") if name.strip()
    }
    
    # RSS采集（官网 / 媒体）
    if "rss" in selected_sources:
        rss_crawler = RSSCrawler(config.RSS_SOURCES, config.RSS_CRAWLER_CONFIG)
        rss_items = rss_crawler.crawl(hours=config.TIME_RANGE_HOURS)
        all_items.extend(rss_items)
    
    # X 采集
    if "x" in selected_sources and config.X_API_CONFIG.get("enabled"):
        x_crawler = XCrawler(config.X_API_CONFIG, config.X_SOURCES)
        x_items = x_crawler.crawl(hours=config.TIME_RANGE_HOURS)
        all_items.extend(x_items)
    
    # Product Hunt AI 产品
    if "product_hunt" in selected_sources and config.PRODUCT_HUNT_CONFIG.get("enabled"):
        product_hunt_crawler = ProductHuntCrawler(config.PRODUCT_HUNT_CONFIG)
        product_hunt_items = product_hunt_crawler.crawl(hours=config.TIME_RANGE_HOURS)
        all_items.extend(product_hunt_items)

    # 小红书创作者
    if "xiaohongshu" in selected_sources and config.XIAOHONGSHU_CONFIG.get("enabled"):
        xhs_crawler = XiaohongshuCrawler(config.XIAOHONGSHU_CONFIG, config.XIAOHONGSHU_SOURCES)
        xhs_items = xhs_crawler.crawl(hours=config.TIME_RANGE_HOURS)
        all_items.extend(xhs_items)

    # Nexttoken 官网 / 新闻 / 工具站点
    if "site" in selected_sources and config.SITE_CRAWLER_CONFIG.get("enabled"):
        site_crawler = SiteCrawler(config.SITE_SOURCES, config.SITE_CRAWLER_CONFIG)
        site_items = site_crawler.crawl(hours=config.TIME_RANGE_HOURS)
        all_items.extend(site_items)

    # 微信公众号
    if "wechat" in selected_sources and config.WECHAT_CONFIG.get("enabled"):
        wechat_crawler = WechatCrawler(config.WECHAT_CONFIG, config.WECHAT_SOURCES)
        wechat_items = wechat_crawler.crawl(hours=config.TIME_RANGE_HOURS)
        all_items.extend(wechat_items)

    # Instagram 创作者
    if "instagram" in selected_sources and config.INSTAGRAM_CONFIG.get("enabled"):
        instagram_crawler = InstagramCrawler(config.INSTAGRAM_CONFIG, config.INSTAGRAM_SOURCES)
        instagram_items = instagram_crawler.crawl(hours=config.TIME_RANGE_HOURS)
        all_items.extend(instagram_items)

    # Reddit 社区 seed
    if "reddit" in selected_sources and config.REDDIT_CONFIG.get("enabled"):
        reddit_crawler = RedditCrawler(config.REDDIT_CONFIG, config.REDDIT_SOURCES)
        reddit_items = reddit_crawler.crawl(hours=config.TIME_RANGE_HOURS)
        all_items.extend(reddit_items)
    
    print(f"\n总计采集: {len(all_items)} 条")
    
    if not all_items:
        print("\n⚠️ 未采集到任何资讯，请检查网络连接和RSS源配置")
        return

    raw_output_dir = Path(config.OUTPUT_DIR)
    raw_output_dir.mkdir(parents=True, exist_ok=True)
    raw_items_path = raw_output_dir / "raw_items.json"
    raw_items_path.write_text(
        json.dumps([item.to_dict() for item in all_items], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"📦 原始条目已保存: {raw_items_path}")

    # 2. 处理
    print("\n🧠 运行处理流水线...")
    print("-" * 50)
    digest_path = run_processing_pipeline(raw_items_path, raw_output_dir)
    digest = load_digest(digest_path)
    print(f"📰 规范 digest 已生成: {digest_path}")

    # 3. 展示 / 邮件
    print("\n🖼️ 生成展示预览...")
    print("-" * 50)
    sender = EmailSender(config.EMAIL_CONFIG)
    sender.build_preview_assets(digest, output_dir=config.OUTPUT_DIR)
    print(f"📄 预览文件已生成: {Path(config.OUTPUT_DIR) / 'preview.html'}")
    workspace_root = Path(__file__).resolve().parents[3]
    site_data_path = workspace_root / "website" / "data" / "site-data.js"
    site_data = build_site_data(digest_path, archive_dir=workspace_root / "output" / "runs")
    write_site_data(site_data_path, site_data)
    print(f"🌐 网站数据已更新: {site_data_path}")

    if args.dry_run:
        print("\n" + "=" * 50)
        print("✨ Dry run 完成")
        print("=" * 50)
        return

    print("\n📬 准备发送邮件...")
    print("-" * 50)
    dispatch_result = dispatch_digest_to_subscribers(
        digest,
        config.EMAIL_CONFIG,
        output_dir=config.OUTPUT_DIR,
        dry_run=False,
    )
    if dispatch_result.get("used_registry"):
        print(f"📮 已按订阅表发送 {len(dispatch_result.get('sent', []))} 封邮件")
        skipped = dispatch_result.get("skipped") or []
        if skipped:
            print(f"⚠️ 跳过 {len(skipped)} 个订阅：{', '.join(entry['email'] for entry in skipped)}")
    else:
        sender.send_digest(digest, output_dir=config.OUTPUT_DIR, dry_run=False)

    print("\n" + "=" * 50)
    print("✨ 完成！")
    print("=" * 50)


if __name__ == "__main__":
    main()
