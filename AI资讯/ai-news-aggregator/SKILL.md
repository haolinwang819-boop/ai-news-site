---
name: ai-news-aggregator
description: 自动化 AI 资讯采集与邮件发送工具。当前代码以 RSS 为主，但目标来源体系已扩展到 Nexttoken 文档中的 X、Instagram、小红书、公众号、AI官网、新闻站点、研究站点与 Reddit。用于采集器代码维护、配置采集源、测试邮件和逐步扩展 daily digest。
---

# AI资讯自动化采集器

This project skill is for the concrete code under `AI资讯/ai-news-aggregator`.

The source inventory should now be read from:
- [../../skills/01-collection/references/nexttoken-source-registry.md](../../skills/01-collection/references/nexttoken-source-registry.md)
- [../../Nexttoken.docx](../../Nexttoken.docx)

Important: the current implementation does not yet cover the full inventory. It is still primarily RSS-based.

Mandatory daily source outside the DOCX inventory: `Product Hunt` daily leaderboard AI top 8. Do not treat it as optional.

## 快速开始

### 1. 配置环境

```bash
pip install requests beautifulsoup4 feedparser python-dateutil cloudscraper
cp scripts/config_template.py scripts/config.py
```

### 2. 编辑配置

编辑 `scripts/config.py`：

```python
EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "your-email@gmail.com",
    "sender_password": "your-app-password",
    "recipient_email": "recipient@example.com"
}
```

### 3. 运行

```bash
python scripts/main.py
python scripts/main.py --dry-run
python scripts/main.py --test-email
```

## Target Platforms From The Inventory

- `X`
- `Instagram`
- `小红书`
- `公众号`
- `Product Hunt`
- `AI官网 / 产品站点`
- `新闻 / 研究 / 会议信源`
- `Reddit`

## Current Code Reality

- Implemented now: RSS collection, `Product Hunt` collection, email preview/send
- Not fully implemented yet: the full Nexttoken social inventory and cross-platform canonicalization

When expanding the code, sync the inventory first, then add the crawler implementation.

## 核心脚本

| 脚本 | 用途 |
|-----|-----|
| `scripts/main.py` | 主调度程序 |
| `scripts/crawlers/` | 各平台爬虫 |
| `scripts/processor.py` | 数据去重、分类、排序 |
| `scripts/email_sender.py` | 邮件发送 |

## Expansion Rules

- Keep the source inventory outside hardcoded crawler lists as much as possible.
- Add timeout, retry, and per-source failure isolation for every new collector.
- Preserve `platform` and `source_type` metadata when wiring new sources into the pipeline.
- Prefer official blog or changelog URLs over noisy homepages when adding tool/product sites.
- Keep `Product Hunt` in the default daily source list and preserve its ranking metadata for `AI黑马产品`.

## References

- [references/platforms.md](references/platforms.md)
- [../../skills/01-collection/references/nexttoken-source-registry.md](../../skills/01-collection/references/nexttoken-source-registry.md)
