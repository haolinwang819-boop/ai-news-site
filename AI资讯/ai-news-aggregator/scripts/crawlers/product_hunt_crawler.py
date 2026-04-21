"""
Product Hunt AI leaderboard crawler.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, List

import cloudscraper
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .base import BaseCrawler, NewsItem

APOLLO_TRANSPORT_PREFIX = '(window[Symbol.for("ApolloSSRDataTransport")] ??= []).push('

AI_TOPIC_SLUGS = {
    "artificial-intelligence",
    "ai-agents",
    "generative-ai",
    "llms",
    "machine-learning",
    "voice-ai",
}

AI_TEXT_CUES = (
    " ai ",
    ".ai",
    "agent",
    "agents",
    "artificial intelligence",
    "assistant",
    "audio model",
    "claude",
    "copilot",
    "foundation model",
    "generative",
    "gpt",
    "llm",
    "machine learning",
    "mcp",
    "model",
    "models",
    "speech",
    "text-to-speech",
    "voice ai",
)

DETAIL_STOPWORDS = {
    "about",
    "across",
    "agent",
    "agents",
    "artificial",
    "built",
    "feature",
    "features",
    "launch",
    "new",
    "platform",
    "product",
    "review",
    "software",
    "system",
    "tool",
    "tools",
    "with",
}


class ProductHuntCrawler(BaseCrawler):
    """Collect the current daily leaderboard and keep the first 8 AI products."""

    def __init__(self, config: dict):
        super().__init__("Product Hunt Crawler")
        self.config = config
        self.top_n = min(int(config.get("top_n", 8)), 8)
        self.priority = int(config.get("priority", 1))
        self.timeout_seconds = int(config.get("timeout_seconds", 30))
        self.max_page_items = int(config.get("max_page_items", 20))
        self.url_template = config.get(
            "leaderboard_url_template",
            "https://www.producthunt.com/leaderboard/daily/{year}/{month}/{day}?ref=header_nav",
        )
        self.fixed_url = str(config.get("leaderboard_url", "")).strip()
        self.fixed_date = str(config.get("leaderboard_date", "")).strip()
        self.session = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "darwin", "desktop": True}
        )
        self.session.headers.update(
            {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
                ),
            }
        )

    def crawl(self, hours: int = 24) -> List[NewsItem]:
        target_date = self._resolve_target_date()
        leaderboard_url = self._build_leaderboard_url(target_date)
        response = self.session.get(leaderboard_url, timeout=self.timeout_seconds)
        response.raise_for_status()

        posts = self._extract_leaderboard_posts(response.text)
        ai_posts = [post for post in posts if self._is_ai_post(post)]
        ranked_ai_posts = ai_posts[: self.top_n]

        items = []
        for post in ranked_ai_posts:
            enriched_post = dict(post)
            product_slug = enriched_post.get("product_slug") or enriched_post.get("slug") or ""
            product_url = f"https://www.producthunt.com/products/{product_slug}" if product_slug else leaderboard_url
            enriched_post.update(self._fetch_product_details(product_url))
            items.append(self._post_to_item(post=enriched_post, leaderboard_url=leaderboard_url))
        print(f"✓ Product Hunt AI leaderboard: 获取 {len(items)} 条")
        return items

    def _resolve_target_date(self) -> datetime:
        if self.fixed_date:
            return date_parser.parse(self.fixed_date)
        return datetime.now()

    def _build_leaderboard_url(self, target_date: datetime) -> str:
        if self.fixed_url:
            return self.fixed_url
        return self.url_template.format(
            year=target_date.year,
            month=target_date.month,
            day=target_date.day,
        )

    def _extract_leaderboard_posts(self, html: str) -> list[dict[str, Any]]:
        start = html.find(APOLLO_TRANSPORT_PREFIX)
        if start < 0:
            raise ValueError("未找到 Product Hunt leaderboard 数据")

        end = html.find("</script>", start)
        if end < 0:
            raise ValueError("Product Hunt leaderboard 数据不完整")

        payload = html[start:end]
        payload = payload.split(".push(", 1)[1].rsplit(")", 1)[0]
        payload = payload.replace(":undefined", ":null")
        transport = json.loads(payload)

        edges = self._find_homefeed_edges(transport.get("rehydrate", {}))
        posts: list[dict[str, Any]] = []

        for edge in edges:
            node = edge.get("node") or {}
            if node.get("__typename") != "Post":
                continue

            rank_value = node.get("dailyRank")
            if rank_value is None:
                continue

            try:
                daily_rank = int(rank_value)
            except (TypeError, ValueError):
                continue

            posts.append(
                {
                    "name": str(node.get("name") or "").strip(),
                    "slug": str(node.get("slug") or "").strip(),
                    "tagline": str(node.get("tagline") or "").strip(),
                    "daily_rank": daily_rank,
                    "created_at": str(node.get("createdAt") or "").strip(),
                    "product_slug": str((node.get("product") or {}).get("slug") or "").strip(),
                    "topic_slugs": [
                        str(topic.get("node", {}).get("slug") or "").strip()
                        for topic in (node.get("topics") or {}).get("edges", [])
                        if topic.get("node")
                    ],
                    "topic_names": [
                        str(topic.get("node", {}).get("name") or "").strip()
                        for topic in (node.get("topics") or {}).get("edges", [])
                        if topic.get("node")
                    ],
                }
            )

        posts.sort(key=lambda post: post["daily_rank"])
        return posts[: self.max_page_items]

    def _find_homefeed_edges(self, rehydrate: dict[str, Any]) -> list[dict[str, Any]]:
        for value in rehydrate.values():
            data = value.get("data")
            if not isinstance(data, dict):
                continue
            homefeed = data.get("homefeedItems")
            if isinstance(homefeed, dict) and isinstance(homefeed.get("edges"), list):
                return homefeed["edges"]
        raise ValueError("未找到 Product Hunt homefeedItems")

    def _is_ai_post(self, post: dict[str, Any]) -> bool:
        topic_slugs = {slug.lower() for slug in post.get("topic_slugs", []) if slug}
        if topic_slugs.intersection(AI_TOPIC_SLUGS):
            return True

        text = " ".join(
            part
            for part in (
                post.get("name", ""),
                post.get("tagline", ""),
                post.get("slug", ""),
            )
            if part
        ).lower()

        return any(self._contains_text_cue(text, cue) for cue in AI_TEXT_CUES)

    def _contains_text_cue(self, text: str, cue: str) -> bool:
        token = cue.lower()
        if token.startswith(" ") or token.endswith(" "):
            return token in f" {text} "
        if re.search(r"[^a-z0-9.]", token):
            return token in text
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])")
        return bool(pattern.search(text))

    def _fetch_product_details(self, product_url: str) -> dict[str, Any]:
        try:
            response = self.session.get(product_url, timeout=self.timeout_seconds)
            response.raise_for_status()
        except Exception:
            return {}

        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        details: dict[str, Any] = {
            "detail_description": self._read_meta_content(soup, "description") or self._read_meta_content(soup, "og:description"),
            "detail_image_url": self._read_meta_content(soup, "og:image"),
            "logo_url": "",
            "product_tagline": "",
            "category_names": [],
        }

        try:
            transport = self._extract_apollo_transport(html)
            product = self._find_product_payload(transport.get("rehydrate", {}))
            if product:
                structured_data = product.get("structuredData") or {}
                details["detail_description"] = (
                    str(structured_data.get("description") or product.get("description") or details["detail_description"] or "").strip()
                )
                details["detail_image_url"] = str(structured_data.get("image") or details["detail_image_url"] or "").strip()
                logo_uuid = str(product.get("logoUuid") or "").strip()
                if logo_uuid:
                    details["logo_url"] = f"https://ph-files.imgix.net/{logo_uuid}?auto=format"
                details["product_tagline"] = str(product.get("tagline") or "").strip()
                details["category_names"] = [
                    str(category.get("name") or "").strip()
                    for category in (product.get("categories") or [])
                    if category.get("name")
                ]
        except Exception:
            pass

        return details

    def _extract_apollo_transport(self, html: str) -> dict[str, Any]:
        start = html.find(APOLLO_TRANSPORT_PREFIX)
        if start < 0:
            raise ValueError("未找到 Product Hunt Apollo 数据")
        end = html.find("</script>", start)
        if end < 0:
            raise ValueError("Product Hunt Apollo 数据不完整")
        payload = html[start:end]
        payload = payload.split(".push(", 1)[1].rsplit(")", 1)[0]
        payload = payload.replace(":undefined", ":null")
        return json.loads(payload)

    def _find_product_payload(self, rehydrate: dict[str, Any]) -> dict[str, Any] | None:
        for value in rehydrate.values():
            data = value.get("data")
            if not isinstance(data, dict):
                continue
            product = data.get("product")
            if isinstance(product, dict) and product.get("__typename") == "Product":
                return product
        return None

    def _read_meta_content(self, soup: BeautifulSoup, key: str) -> str:
        tag = soup.find("meta", attrs={"name": key}) or soup.find("meta", attrs={"property": key})
        if not tag:
            return ""
        return str(tag.get("content") or "").strip()

    def _dedupe_segments(self, segments: list[str]) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for segment in segments:
            cleaned = re.sub(r"\s+", " ", str(segment or "")).strip()
            if not cleaned:
                continue
            normalized = re.sub(r"[^a-z0-9]+", " ", cleaned.lower()).strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(cleaned)
        return deduped

    def _detail_matches_launch(self, post: dict[str, Any], detail: str) -> bool:
        launch_tokens = self._detail_tokens(post.get("name", ""), post.get("tagline", ""))
        detail_tokens = self._detail_tokens(detail)
        if not launch_tokens or not detail_tokens:
            return False
        return len(launch_tokens.intersection(detail_tokens)) >= 2

    def _detail_tokens(self, *parts: str) -> set[str]:
        text = " ".join(str(part or "") for part in parts).lower()
        tokens = {
            token
            for token in re.findall(r"[a-z0-9]{4,}", text)
            if token not in DETAIL_STOPWORDS
        }
        return tokens

    def _post_to_item(self, post: dict[str, Any], leaderboard_url: str) -> NewsItem:
        published = date_parser.parse(post["created_at"]) if post.get("created_at") else datetime.now()
        product_slug = post.get("product_slug") or post.get("slug") or ""
        product_url = f"https://www.producthunt.com/products/{product_slug}" if product_slug else leaderboard_url
        topic_names = post.get("category_names") or post.get("topic_names") or []
        topics = ", ".join(name for name in topic_names if name)
        product_tagline = post.get("product_tagline") or ""
        detail_description = post.get("detail_description") or ""
        if product_tagline and not self._detail_matches_launch(post, product_tagline):
            product_tagline = ""
        if detail_description and not self._detail_matches_launch(post, detail_description):
            detail_description = ""
        segments = self._dedupe_segments(
            [
                post.get("tagline") or "",
                product_tagline,
                detail_description,
                f"Product categories: {topics}." if topics else "",
            ]
        )
        content = " ".join(segment if segment.endswith((".", "!", "?")) else f"{segment}." for segment in segments).strip()
        summary = (detail_description or post.get("tagline") or product_tagline or post.get("name") or "Product Hunt AI launch").strip()

        return NewsItem(
            title=post.get("name") or "Product Hunt AI Product",
            summary=summary.strip(),
            url=product_url,
            source="Product Hunt",
            published_time=published,
            content=content or summary.strip(),
            image_url=post.get("detail_image_url") or None,
            logo_url=post.get("logo_url") or None,
            platform="site",
            source_type="media",
            source_url=leaderboard_url,
            product_rank=post["daily_rank"],
            priority=self.priority,
        )
