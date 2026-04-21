# 数据源配置

## RSS源列表

### AI官网博客

| 来源 | RSS URL | 优先级 |
|-----|---------|-------|
| OpenAI Blog | https://openai.com/blog/rss.xml | P0 |
| Anthropic News | https://www.anthropic.com/feed.xml | P0 |
| Google AI Blog | https://blog.google/technology/ai/rss/ | P0 |
| DeepMind Blog | https://deepmind.google/blog/rss.xml | P0 |
| Meta AI | https://ai.meta.com/blog/rss/ | P1 |

### 新闻媒体

| 来源 | RSS URL | 优先级 |
|-----|---------|-------|
| The Verge AI | https://www.theverge.com/rss/ai-artificial-intelligence/index.xml | P1 |
| TechCrunch AI | https://techcrunch.com/category/artificial-intelligence/feed/ | P1 |
| VentureBeat AI | https://venturebeat.com/category/ai/feed/ | P1 |
| Ars Technica AI | https://feeds.arstechnica.com/arstechnica/technology-lab | P2 |

### 中文媒体

| 来源 | RSS URL | 优先级 |
|-----|---------|-------|
| 机器之心 | https://www.jiqizhixin.com/rss | P1 |
| 量子位 | https://www.qbitai.com/feed | P1 |
| 新智元 | https://mp.weixin.qq.com (需专门适配) | P2 |

---

## X平台配置

### 方式1：使用官方API（推荐）

1. 访问 https://developer.twitter.com 申请API
2. 获取 Bearer Token
3. 在 config.py 中填入：

```python
X_API_CONFIG = {
    "enabled": True,
    "bearer_token": "YOUR_BEARER_TOKEN",
    "search_queries": [
        "AI news",
        "GPT-5",
        "Claude",
        "Midjourney",
        "Sora"
    ]
}
```

### 方式2：禁用X采集

```python
X_API_CONFIG = {
    "enabled": False
}
```

---

## 小红书/抖音采集

由于这些平台反爬机制严格，建议使用以下替代方案：

1. **关注关键账号的RSS转换服务**（如RSSHub）
2. **使用官方开放API**（如有）
3. **手动整理重点内容**

如需自动采集，需自行配置Selenium + 登录态cookie。

---

## 添加新数据源

在 `scripts/crawlers/rss_crawler.py` 中添加：

```python
RSS_SOURCES.append({
    "name": "新来源名称",
    "url": "https://example.com/feed.xml",
    "category": "ai_news",  # 默认分类
    "priority": 2
})
```
