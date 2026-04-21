---
name: ai-news-processing
description: AI资讯信息处理 Skill。负责将来自 Nexttoken 来源体系的原始资讯做标准化、来源分级、分类、去重和反思，输出日报 JSON。当用户提到“处理资讯”“分类资讯”“去重”“来源分级”“生成日报JSON”时触发。
---

# 信息处理 Skill

This skill turns heterogeneous source items into a ranked digest.

It sits after 01-collection and should assume the input may come from:
- official sites and blogs
- official social accounts
- media and newsletters
- creator accounts on X / Instagram / Xiaohongshu / WeChat
- research and conference sources
- community discussion such as Reddit

When the source identity matters, load [../01-collection/references/nexttoken-source-registry.md](../01-collection/references/nexttoken-source-registry.md).

## 处理流程

```text
原始条目 → 标准化 → 分类 → 去重 → 反思 ──┐
                ▲                          │
                └──── 若 need_rerun ───────┘
                     (最多 2 轮)
```

## Normalize First

Before classification, make sure every item carries consistent provenance:
- `title`
- `url`
- `source`
- `platform`
- `source_type`
- `published_time`
- `content`
- optional `image_url`, `author_handle`, `source_url`

If the collector only captured a short social post, keep the raw text and do not invent missing facts.

## Authority Ranking

Use rough source precedence like this during priority assignment and dedup:

1. official site or official blog
2. official social post that directly announces or links to the release
3. top-tier media report
4. creator analysis, demo, or commentary
5. community discussion

Reddit and repost-heavy creator content should almost never outrank official or credible media coverage.

## Category Mapping

| 代码 key | 展示名 | 内容范围 |
|----------|--------|---------|
| `breakout_products` | AI黑马产品 | 仅保留 Product Hunt 当天 AI 榜前 8，以及极少数明确爆火的新 AI 应用产品。这里必须是新产品，不是老产品更新，也不是模型上新。 |
| `hot_news` | AI热点资讯 | 政策、并购、融资、诉讼、芯片、创始人流动、重大行业事件。不要把博主观点或一般性产品介绍放进来。 |
| `llm` | AI基模 | 基础模型发布、版本更新、推理/记忆/协同等模型或模型平台能力升级。 |
| `image_video` | AI多模态 | 生图、生视频、音频、视觉理解、多模态模型与多模态产品能力更新。 |
| `product_updates` | AI热门产品更新汇总 | 头部 AI 产品的新功能、新模式、新工作流更新，如 Notion、Character AI、Lovart、Superhuman、GitHub Copilot 等。 |

Keep classification based on the event itself, not just the source platform. An X post can still belong to `llm` or `image_video` if it announces a model release.

Product Hunt handling rule:
- Daily `Product Hunt` leaderboard items should enter `breakout_products` only after filtering to AI products and keeping the first 8 AI items in leaderboard order.
- Keep the fact that an item came from `Product Hunt`, because the display layer uses that attribution for the `AI黑马产品` block.

## 四个节点详解

### 1. 标准化节点 (`normalize`)

- **Prompt**：`AI资讯/ai-news-processing/prompts/normalize.md`
- **输入**：原始抓取条目（字段可能缺失或不统一）
- **输出**：统一字段格式的条目，赋予 `priority`（0重磅/1重要/2日常/3其他）
- **不做分类**：`category` 留空，由下一节点处理
- **要求**：保留来源元数据，不要把 `platform`、`source_type`、`author_handle` 等信息洗掉

### 2. 分类节点 (`classify`)

- **Prompt**：`AI资讯/ai-news-processing/prompts/classify.md`
- **输入**：标准化后的条目
- **输出**：每条增加 `category` 字段（四选一）
- **规则**：每条只能属于一个板块；无法明确归入前三个则归入 `hot_news`

### 3. 去重节点 (`dedup`)

- **Prompt**：`AI资讯/ai-news-processing/prompts/dedup.md`
- **输入**：已分类的条目
- **输出**：合并/删除重复项后的条目
- **去重规则**：
  - URL 相同 → 只保留一条
  - 同事件跨平台重复 → 保留最权威来源作为主条目
  - 官方博客 + 官方 X 帖子 + 媒体报道通常属于同一事件簇
  - 创作者实测、拆解、基准测试如果提供新增信息，可作为独立条目保留

### 4. 反思节点 (`reflect`)

- **Prompt**：`AI资讯/ai-news-processing/prompts/reflect.md`
- **输入**：去重后的条目
- **输出**：`{ "need_rerun": bool, "issues": [...] }`
- **检查**：错分、漏并、同条多板块、缺失关键信息
- **额外检查**：是否被低权威信源带偏；是否缺少更高权威的 canonical source
- **回流**：若 `need_rerun=true` 且未超过最大轮数（2），回到分类节点重新处理

## Output Contract

The digest JSON should be ready for 03-display and 04-delivery. At minimum each final item should preserve:
- `title`
- `url`
- `source`
- `published_time`
- `priority`
- `category`
- `content`
- `image_url`

If available, keep `platform` and `source_type` too. They help the display layer show better attribution.

For the final reader-facing digest, each displayed item should also include:
- `display_title`: rewritten English headline, not copied verbatim from the source title
- `summary`: English 2-3 sentence summary based on the scraped material
- `key_points`: exactly 3 English bullets that surface the most important takeaways

These display fields should be grounded in the crawled content. They are editorial outputs, not raw-source passthrough fields.

## 运行方式

```bash
cd AI资讯/ai-news-processing

# 安装依赖
pip install -r requirements.txt

# 设置 LLM API Key
export OPENAI_API_KEY=sk-...
# 或使用 Anthropic:
# export ANTHROPIC_API_KEY=... && export LLM_PROVIDER=anthropic

# 运行管线
python run.py path/to/items.json

# 或从 stdin
cat items.json | python run.py -
```

输出写入 `data/digests/YYYY-MM-DD.json`。

## 核心脚本

| 脚本 | 作用 |
|-----|------|
| `scripts/pipeline.py` | LangGraph 图定义 + 四个节点实现 + ProcessingPipeline 类 |
| `scripts/models.py` | PipelineItem 数据结构 + PipelineState 图状态 |
| `scripts/llm_utils.py` | Prompt 加载（{{变量}}替换）+ LLM 调用封装 + JSON 输出解析 |
| `scripts/config.py` | 路径、LLM 配置、反思最大轮数 |
| `scripts/run.py` | CLI 入口：读输入 → 跑管线 → 写日报文件 |

## References

- [../../AI资讯/ai-news-processing/处理流程与数据规范.md](../../AI资讯/ai-news-processing/处理流程与数据规范.md)
- [../01-collection/references/nexttoken-source-registry.md](../01-collection/references/nexttoken-source-registry.md)
