---
name: ai-news-collection
description: AI资讯信息源采集 Skill。负责基于 Nexttoken 来源清单维护和执行多平台采集，包括 X、Instagram、小红书、公众号、AI官网、新闻站点、研究站点与 Reddit。当用户提到“采集资讯”“抓取新闻”“扩充来源”“配置爬虫”“维护来源清单”时触发。
---

# 信息源采集 Skill

This skill owns source coverage and raw collection for the daily AI digest.

The canonical allowlist is [../../../Nexttoken.docx](../../../Nexttoken.docx). Do not duplicate the full list inside the SKILL body. Use:
- [references/nexttoken-source-registry.md](references/nexttoken-source-registry.md) for the normalized navigation layer
- [scripts/extract_nexttoken_sources.sh](scripts/extract_nexttoken_sources.sh) when you need the exact source names and links from the DOCX

Fixed supplemental source outside the DOCX:
- `Product Hunt` daily leaderboard AI launches. This is a required daily source, not an optional add-on.

## Use This Skill For

- adding, removing, or auditing sources from the daily digest inventory
- deciding the crawl method for a platform or source family
- defining raw item schema and collector output
- checking whether a source should be treated as `official`, `media`, `creator`, `community`, or `research`
- comparing coverage gaps between the codebase and the Nexttoken allowlist

## Registry Workflow

1. Start with `extract_nexttoken_sources.sh summary`.
2. Load only the section you need: `x`, `instagram`, `xhs`, `wechat`, `tools`, `news`, or `reddit`.
3. Map each source to:
   - `platform`
   - `source_type`
   - `crawl_method`
   - `auth_requirement`
   - `priority_hint`
4. Keep the registry as the source inventory; keep project config files as implementation detail.
5. Keep `Product Hunt` as a permanent supplemental source even if it is absent from the DOCX.
6. If the DOCX changes, update the registry reference before editing crawler configs.

## Platform Collection Rules

- `X`: high-signal discovery for official launches, founder commentary, and devtool updates. Prefer API or authenticated collection. Preserve `author_handle` and `post_url`.
- `Instagram`: creator-discovery only. Low authority. Keep profile URL and post URL separate if both exist.
- `小红书`: explicit allowlist only. Expect authenticated or semi-manual collection. Preserve creator name and the `xhslink.com` URL.
- `公众号`: curated channel list only. Favor mirrored/article-forward workflows over brittle scraping.
- `Product Hunt`: mandatory daily source. Collect the current daily leaderboard, filter AI products only, and keep the first 8 AI items every run. Preserve leaderboard rank, product URL, tagline, and launch date when available.
- `AI官网 / product sites`: prefer changelog, blog, docs, release notes, or newsroom pages over generic homepages.
- `新闻 / 研究 / 会议信源`: prefer RSS and structured article pages; use them for context, benchmarks, research, and third-party reporting.
- `Reddit`: community signal only. Do not treat as a primary fact source.

## Daily Coverage Rules

- Do not shrink the allowlist for convenience. The expected behavior is full coverage of the Nexttoken inventory plus `Product Hunt`.
- `Product Hunt` must run on every daily job, even if some other source groups are temporarily disabled for debugging.
- For `Product Hunt`, the collection target is the current daily leaderboard with AI-only filtering, then the first 8 AI products in leaderboard order. Do not use a random subset or a historical archive pull.

## Raw Item Contract

Every collected item should preserve the fields below before entering 02-processing:

| Field | Required | Notes |
|---|---|---|
| `title` | yes | post headline or synthesized short title |
| `url` | yes | canonical article/post URL |
| `source` | yes | publication name, account name, or site name |
| `platform` | yes | `x`, `instagram`, `xiaohongshu`, `wechat`, `site`, `news`, `research`, `reddit` |
| `source_type` | yes | `official`, `media`, `creator`, `community`, `research` |
| `published_time` | yes | ISO8601 when possible |
| `content` | yes | body text, excerpt, or post text |
| `image_url` | no | primary visual if available |
| `author_handle` | no | especially for social sources |
| `source_url` | no | profile URL, channel URL, or site root |

Do not assign `priority` or `category` here. That belongs to 02-processing.

## Current Codebase Implication

The current code under `AI资讯/ai-news-aggregator` only covers a subset of this inventory. When expanding collection:
- update the registry first
- then add the crawler implementation
- then map the new output into the raw item contract above

## References

- [references/nexttoken-source-registry.md](references/nexttoken-source-registry.md)
- [../../AI资讯/ai-news-aggregator/references/platforms.md](../../AI资讯/ai-news-aggregator/references/platforms.md)
