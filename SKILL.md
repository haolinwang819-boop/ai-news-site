---
name: ai-news-workflow
description: AI资讯日更工作流总控 Skill。负责在来源清单、采集、处理、展示、发布之间做路由和约束，特别适用于用户要维护 Nexttoken 来源体系、检查日更链路、或重构 daily AI digest 流程时。
---

# AI 资讯工作流 Skill

This is the entry-point skill for the daily AI digest system.

The current source-of-truth allowlist is [Nexttoken.docx](Nexttoken.docx). The normalized navigation layer is [skills/01-collection/references/nexttoken-source-registry.md](skills/01-collection/references/nexttoken-source-registry.md).

Mandatory supplemental source outside the DOCX: `Product Hunt` daily leaderboard AI launches. Every daily run should scan the current daily leaderboard, filter AI products only, and keep the first 8 AI items for `AI黑马产品`.

## Use This Skill For

- auditing whether the daily digest can run end to end
- updating skills after the source inventory changes
- deciding which stage skill should own a task
- aligning the raw-item schema across collection, processing, display, and delivery
- reviewing what is still missing before the daily AI digest is reliable

## Stage Routing

- source inventory, crawler coverage, platform mapping:
  [skills/01-collection/SKILL.md](skills/01-collection/SKILL.md)
- normalization, authority ranking, category assignment, dedup, digest JSON:
  [skills/02-processing/SKILL.md](skills/02-processing/SKILL.md)
- markdown cards, email content, web display formatting:
  [skills/03-display/SKILL.md](skills/03-display/SKILL.md)
- smtp, web publishing, preview, scheduling:
  [skills/04-delivery/SKILL.md](skills/04-delivery/SKILL.md)

## Canonical Handoff Contract

01-collection should emit raw items with:
- `title`
- `url`
- `source`
- `platform`
- `source_type`
- `published_time`
- `content`
- optional `image_url`, `author_handle`, `source_url`

02-processing adds:
- `priority`
- `category`
- optional supporting metadata needed for display

03-display turns processed items into markdown or HTML-ready content.

04-delivery publishes only the processed and formatted result.

## Source-Aware Rules

- Official blogs and sites outrank reposts and commentary.
- Official social posts are strong supporting sources, but should not replace a better canonical launch URL.
- Creator and community sources are useful for discovery, workflows, and sentiment, but need clearer labeling.
- Reddit is a weak signal unless corroborated elsewhere.

## Daily Run Order

1. sync source coverage with `Nexttoken.docx`
2. collect raw items from the relevant platforms
3. always collect `Product Hunt` daily leaderboard AI top 8, even if it is not listed inside `Nexttoken.docx`
4. normalize, rank, classify, and deduplicate
5. generate display output
6. preview
7. send or publish

## References

- [skills/01-collection/references/nexttoken-source-registry.md](skills/01-collection/references/nexttoken-source-registry.md)
- [skills/01-collection/SKILL.md](skills/01-collection/SKILL.md)
- [skills/02-processing/SKILL.md](skills/02-processing/SKILL.md)
- [skills/03-display/SKILL.md](skills/03-display/SKILL.md)
- [skills/04-delivery/SKILL.md](skills/04-delivery/SKILL.md)
