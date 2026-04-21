# Nexttoken Source Registry

This file is the normalized navigation layer for [Nexttoken.docx](/Users/haolinwang/Desktop/AI资讯 2/Nexttoken.docx), which is the current source-of-truth allowlist for the AI news pipeline.

Use this reference when the task involves:
- adding or auditing crawl coverage
- deciding which platform-specific collector to build
- checking whether a source is official, media, creator, or community
- updating skills after the allowlist changes

Mandatory supplemental source not stored in the DOCX:
- `Product Hunt` daily leaderboard AI top 8. Treat it as part of the collection contract for every daily run.

## Quick Access

Prefer the helper script when you need exact names and links from the DOCX:

```bash
skills/01-collection/scripts/extract_nexttoken_sources.sh summary
skills/01-collection/scripts/extract_nexttoken_sources.sh x
skills/01-collection/scripts/extract_nexttoken_sources.sh news
```

If you need to inspect the raw document directly:

```bash
textutil -convert txt -stdout Nexttoken.docx
```

## Section Map

| Section | Approx. count | Extract command | Notes |
|---|---:|---|---|
| X accounts | 65 | `extract_nexttoken_sources.sh x` | Founders, labs, model vendors, devtools, curators |
| Instagram | 13 | `extract_nexttoken_sources.sh instagram` | Mostly AI-news creator accounts |
| Xiaohongshu | 28 | `extract_nexttoken_sources.sh xhs` | Chinese creator and tooling accounts |
| WeChat public accounts | 19 | `extract_nexttoken_sources.sh wechat` | Mostly Chinese AI media and creator newsletters |
| AI tools / model / product sites | 158 | `extract_nexttoken_sources.sh tools` | Official product pages and launch surfaces |
| News / research / conference sites | 55 | `extract_nexttoken_sources.sh news` | Media, labs, papers, conferences, trend sites |
| Reddit threads | 1 populated seed | `extract_nexttoken_sources.sh reddit` | Community signal only; not a primary fact source |

## Supplemental Mandatory Source

| Source | Coverage rule | Notes |
|---|---|---|
| `Product Hunt` | collect the current daily leaderboard, filter AI products, and keep the first 8 AI items every run | feeds `AI黑马产品`; preserve ranking, product URL, tagline, and launch metadata |

## Source Families

Use these source families during collection and downstream ranking:

| Source family | Typical platforms | How to use |
|---|---|---|
| `official` | official blogs, product sites, official X accounts | Highest authority for launches, model updates, pricing, policy statements |
| `media` | AI media, tech press, newsletters | Use for industry context, interviews, financing, third-party reporting |
| `creator` | X creators, Instagram accounts, Xiaohongshu accounts | Use as discovery and demo signal; verify major claims before promotion |
| `community` | Reddit, conference chatter, social discussion | Use as weak signal and trend detection; do not elevate without corroboration |
| `research` | arXiv, conference sites, lab blogs | Use for model, paper, benchmark, and architecture developments |

## Platform Playbook

### X

- Treat X as a high-signal discovery layer for founders, labs, and product teams.
- Preserve `author_handle`, `post_url`, and the canonical product or blog URL when a post links out.
- Prefer official accounts over commentary accounts when the same launch appears in both places.
- Good examples from the allowlist:
  - official labs/products: `@OpenAI`, `@AnthropicAI`, `@GoogleDeepMind`, `@GeminiApp`, `@xai`, `@perplexity_ai`, `@Alibaba_Qwen`, `@huggingface`, `@NotebookLM`
  - founders/researchers: `@natfriedman`, `@karpathy`, `@AravSrinivas`, `@sundarpichai`, `@alexandr_wang`, `@DrJimFan`, `@soumithchintala`, `@percyliang`, `@sama`
  - devtools/platforms: `@vercel`, `@rauchg`, `@OpenRouterAI`, `@lmstudio`, `@cerebras`

### Instagram

- Treat as creator discovery, not a primary fact source.
- Many entries in the DOCX are URLs without explicit display names; derive the handle from the URL when normalizing metadata.
- Store the profile URL and post URL separately if you collect individual posts.

### Xiaohongshu

- Use only the explicit allowlist from the DOCX.
- Expect semi-manual or authenticated collection; do not assume anonymous scraping will be stable.
- Preserve the creator name used in the list plus the `xhslink.com` URL.
- Representative creators in the allowlist include: `杜老师AIGC`, `秋芝2046`, `赛文乔伊`, `成也2077`, `清华姜学长`, `赛博鸭AIGC`, `Feng聊AI世界`, `马克张的AI空间`, `科技捕手`, `傅盛`.

### WeChat Public Accounts

- Treat WeChat accounts as curated media or creator channels.
- Expect manual collection, mirrored feeds, or article forwarding workflows rather than a simple open API.
- Preserve the account name exactly as listed in the source inventory.
- Accounts currently listed include:
  - `量子位`
  - `何夕2077`
  - `PlusAITech`
  - `机器之心`
  - `新智元`
  - `智东西`
  - `数字生命卡兹克`
  - `AI前线`
  - `夕小瑶科技说`
  - `AIGC开放社区`
  - `甲子光年`
  - `硅星人Pro`
  - `极客公园`
  - `暗涌Waves`
  - `第一新声`
  - `磐创AI`
  - `机器学习算法那些事`
  - `AI科技评论`
  - `APPSO`

### AI Tools / Model / Product Sites

- Treat these as official product surfaces for launches, changelogs, pricing, and feature updates.
- Do not crawl the homepage blindly if a blog, changelog, docs, or product update page exists.
- The inventory spans several sub-groups:
  - LLM and assistant products: `豆包`, `Kimi`, `文心一言`, `通义千问`, `智谱清言`, `ChatGPT`, `Claude`, `Gemini`, `Perplexity`, `DeepSeek`, `Mistral`
  - office and writing tools: `WPS AI`, `ChatExcel`, `AiPPT`, `Notion AI`, `Grammarly`, `QuillBot`, `SlidesAI`
  - research and search tools: `秘塔AI搜索`, `Consensus`, `Elicit`, `Semantic Scholar`, `Tavily`, `Exa AI`, `Kagi`
  - multimodal image/video: `通义万相`, `即梦AI`, `腾讯ARC`, `Midjourney`, `DALL·E 3`, `Adobe Firefly`, `Runway`, `Kling`, `Vidu AI`
  - audio and voice: `Murf AI`, `Stable Audio`, `Riffusion`, `WellSaid Labs`, `Speechify`, `Voicemod AI`, `Podcastle`
  - coding, agents, and automation: `通义灵码`, `CodeGeeX`, `GitHub Copilot`, `Tabnine`, `Sourcegraph Cody`, `Warp`, `Replit AI`, `LangChain`, `LlamaIndex`, `Bolt`, `Coze扣子`, `Zapier AI`, `CrewAI`, `Airflow`
  - 3D and creative tooling: `Meshy AI`, `Tripo AI`, `Spline AI`, `Alpha3D`

### News / Research / Conference Sites

- Use these for third-party reporting, benchmarks, papers, conference news, and trend detection.
- The list mixes AI media, official research blogs, paper repositories, conference sites, and trend surfaces.
- Representative groups:
  - Chinese AI media: `机器之心`, `量子位`, `智东西`, `雷锋网`, `极客公园`
  - English tech media: `MIT Technology Review`, `TechCrunch`, `The Verge`, `Wired`, `VentureBeat`, `ZDNet`
  - official research blogs: `OpenAI Blog`, `Google AI Blog`, `DeepMind Blog`, `Microsoft Research Blog`, `Amazon Science`, `Apple Machine Learning`, `NVIDIA Blog`, `IBM Research Blog`
  - research and trend surfaces: `arXiv`, `GitHub Trending`, `Kaggle`, `Towards Data Science`, `IEEE Xplore`, `ACM Digital Library`
  - conferences: `AAAI`, `NeurIPS`, `ICML`, `ICLR`, `CVPR`, `ACL`

### Reddit

- Treat Reddit as community commentary only.
- Keep the thread URL and subreddit if available.
- Never let a Reddit post outrank an official announcement or credible reporting without external confirmation.

## Collection Contract

Raw items should preserve the following fields before they enter processing:

| Field | Required | Notes |
|---|---|---|
| `title` | yes | human-readable title or synthesized post headline |
| `url` | yes | canonical article/post URL |
| `source` | yes | source name, account, or publication name |
| `platform` | yes | `x`, `instagram`, `xiaohongshu`, `wechat`, `site`, `news`, `research`, `reddit` |
| `source_type` | yes | `official`, `media`, `creator`, `community`, `research` |
| `published_time` | yes | ISO8601 when possible |
| `content` | yes | post text, article excerpt, or scraped body |
| `image_url` | no | primary image if available |
| `author_handle` | no | especially for X / Instagram |
| `source_url` | no | profile URL, channel URL, or site root |

## Ranking Guidance

When the same event appears in multiple places, prefer this rough order:

1. official site or official blog
2. official social post that links to the launch
3. top-tier media report
4. creator analysis or demo
5. community discussion

The daily digest should still preserve genuinely distinct angles, but never let weaker sources replace the best available authority.
