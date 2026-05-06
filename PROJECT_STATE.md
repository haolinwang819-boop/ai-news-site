# NextToken AI News Project State

## Product
- Public site: https://nextokenainews.com
- Repository/workspace: `/Users/haolinwang/Desktop/AI资讯 2`
- Production content should be generated locally first, reviewed, then published.
- GitHub Actions is not authoritative for editorial quality yet.

## Editorial Standard
- Website UI and digest output should be English-only.
- Each story needs a rewritten English title, one clear one-sentence summary, and exactly three useful bullet points.
- Reject output with Chinese leakage, repeated bullets, missing bullets, source/debug filler, or titles that simply copy the source title.
- Product Hunt rank can appear in metadata, but bullets should explain why the product matters rather than restating leaderboard position.

## Local Pipeline
- Preferred flow: collect raw items, deterministic prefilter, parallel Gemini Flash screening, Gemini Pro editorial, quality gate, website data build.
- Screening model: Gemini Flash preview.
- Editorial model: Gemini Pro preview.
- Keep Instagram and Xiaohongshu optional/non-blocking unless reliable cookies/API access are available.
- Email sending stays disabled unless explicitly requested.

## Website State
- Current local/default digest after the May 2-5 update: `2026-05-05`.
- Existing site digest files live in `website/data/digests/`.
- Main site data file: `website/data/site-data.js`.
- Date navigation has already been upgraded to Previous day, Choose date, and Next day controls.

## Latest Completed Batch
- Generated high-quality local digests for `2026-05-02`, `2026-05-03`, `2026-05-04`, and `2026-05-05`.
- Synced approved digests into `website/data/digests/`.
- Rebuilt `website/data/site-data.js` so the default/latest date is `2026-05-05`.
- Automatic quality sweep found no Chinese leakage, no missing bullets, and no duplicate bullets in the May 2-5 digests.

## Guardrails
- Do not touch unrelated untracked duplicate files unless requested:
- `AI资讯/ai-news-aggregator/scripts/build_nexttoken_site 2.py`
- `AI资讯/ai-news-processing/scripts/run 2.py`
- `website/app 2.js`
- Actual current Codex session context window was observed as about `258400`, even though local config contains `model_context_window = 800000` and `model_auto_compact_token_limit = 700000`.
