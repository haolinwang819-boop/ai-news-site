---
name: ai-news-display
description: AI资讯信息展示 Skill。负责将处理好的日报 JSON 转成适合网页和邮件的展示内容，并正确表达来源平台与信源级别。当用户提到“生成资讯展示”“格式化日报”“生成邮件日报”“网页卡片”“优化摘要”时触发。
---

# 信息展示 Skill

This skill turns processed digest items into readable output for web pages and email digests.

The source inventory now spans official sites, media, creator social accounts, and community sources. Display should preserve that provenance instead of flattening everything into identical cards.

## 输入数据

从 `data/digests/YYYY-MM-DD.json` 读取日报数据，每条资讯包含以下字段：

| 字段 | 说明 |
|------|------|
| `title` | 资讯标题 |
| `display_title` | AI 重写后的英文标题 |
| `url` | 原文链接 |
| `source` | 信息来源名称 |
| `published_time` | 发布日期 |
| `category` | 所属模块 |
| `priority` | 优先级 0-3 |
| `content` | 正文/摘要 |
| `summary` | 面向读者的英文摘要 |
| `key_points` | 3 个英文 bullet points |
| `image_url` | 配图链接（可选） |

If `platform` and `source_type` are present, display them. They are especially useful now that the source list includes X, Instagram, Xiaohongshu, WeChat, official sites, and Reddit.

All reader-facing copy should be in English, even when the source material is Chinese or mixed-language.
Do not paste the raw source title directly as the final headline. Use an AI-rewritten English `display_title`.
This is the required default for every daily run, not a one-off formatting option.

## 标签匹配

每条资讯需根据内容匹配所属模块的标签。完整标签库见 [../../tag_libraries.md](../../tag_libraries.md)。

**五个模块的标签概览**：

- **AI 黑马产品**：音频类 / 办公类 / 生图生视频类 / 编程开发类 / 教育类 / 聊天对话类
- **AI 热点资讯**：行业动态 / 政策法规 / 人物观点 / 产品发布 / 技术突破 / 市场分析 / 开源动态
- **基模**：大语言模型 / 小模型 / 模型评测 / 训练技术 / 推理优化 / 架构创新 / AI Infra
- **多模态**：文生图 / 文生视频 / 图像编辑 / 音乐生成 / 3D生成 / 视觉理解
- **AI 热门产品更新汇总**：头部产品新功能 / 新模式 / 新工作流 / 新界面 / 新生态集成

**匹配规则**：
1. 每条资讯至少匹配 1 个标签，最多 3 个
2. 优先匹配最具体的标签
3. 以 `category` 字段为准，在该模块标签库内匹配

## Provenance Rules

- `official` sources can be phrased directly as launches, releases, or product updates.
- `media` sources should read as reporting, interviews, analysis, or synthesis.
- `creator` sources should read as demos, observations, workflows, or hands-on takes.
- `community` sources should be labeled as discussion or signal, not as confirmed fact.
- If an item came from a social platform but links to an official launch page, prefer the official link as the main hyperlink.

## Required Reader-Facing Structure

Every displayed item should follow this order:

1. AI-rewritten English headline
2. One English summary paragraph explaining what happened and why it matters
3. Exactly three English bullet points highlighting the key takeaways
4. `Read more` link, date, and a single clean source label such as `Anthropic website`, `The Wall Street Journal`, `X @karpathy`, or `Product Hunt · #1`

The summary and bullets must be derived from the scraped content, not from a fixed template.
Every daily digest run should enforce this structure automatically before preview and delivery.
For `AI黑马产品`, the summary and bullets must go beyond "what the product does". They should surface the product's standout features, strengths, workflow advantages, or launch differentiation when the source supports them.

## 网页展示格式

### 资讯卡片

```markdown
### {display_title}

> **Tags:** `tag1` `tag2`
>
> **Source:** [Read more]({url}) · {publish_date}

{English summary paragraph}

- {key point 1}
- {key point 2}
- {key point 3}

![配图]({image_url})

---
```

### 模块页面结构

```markdown
# {section_name} — {date}

> {N} stories in today's digest

## {tag_group_1}
{cards for this tag group...}

## {tag_group_2}
{cards for this tag group...}
```

完整模板和示例见 [../../display_templates.md](../../display_templates.md)。

Recommended additions when metadata exists:
- keep the metadata line compact: `Read more · date · source label`
- avoid duplicate provenance like `Official Site · Official`
- `Product Hunt` attribution should preserve the leaderboard rank for the daily AI top-8 items

## 邮件展示格式

### 邮件主题

```text
[Daily AI Brief · {module_name}] {date} — {top rewritten headline}
```

### 邮件正文结构

```markdown
# {module_name} · Daily AI Brief

> {date} · {N} stories

---

## Top Stories

1. **{display_title_1}** — {one-sentence English takeaway}
2. **{display_title_2}** — {one-sentence English takeaway}

---

## Full Brief

{cards grouped by category, each with summary + 3 bullets}

---

## 更多

- [Open the full web version]({web_link})
- [Manage subscription settings]({settings_link})
```

### Editorial Rules

1. Every visible sentence should be English.
2. The headline should be rewritten, not copied from the source title.
3. The summary should explain both the event and why it matters.
4. The three bullets should help a reader scan the key points quickly.
5. Avoid hype, speculation, and unsupported claims.
6. For `AI黑马产品`, prefer concrete differentiation over generic category language. Avoid filler like "this is an AI tool" when the source provides richer product detail.

## Ordering Guidance

- Within each category, official launches and high-authority reporting should appear before creator commentary.
- Creator and community items are useful for flavor and signal, but should not dominate the top of the digest.
- If multiple items cover the same event, only the best canonical item should get prominent placement.
- `AI黑马产品` should preserve `Product Hunt` daily launch items when present; do not accidentally filter them out during summarization or formatting.

## 输出要求

1. 所有输出为 `.md` 文件
2. 网页展示命名：`{module_id}_{YYYY-MM-DD}.md`
3. 邮件展示命名：`email_{module_id}_{YYYY-MM-DD}.md`
4. Reader-facing copy must be English-first
5. Each item must show a rewritten title, a summary paragraph, and exactly three bullet points
6. Markdown 语法规范：标题层级清晰，列表缩进统一

## References

- [../../tag_libraries.md](../../tag_libraries.md)
- [../../display_templates.md](../../display_templates.md)
- [../01-collection/references/nexttoken-source-registry.md](../01-collection/references/nexttoken-source-registry.md)
