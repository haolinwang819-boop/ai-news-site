"""
X / Twitter API 爬虫（twitterapi.io）。
"""
from __future__ import annotations

import re
from typing import Any, List

import requests
from dateutil import parser as date_parser

from .base import BaseCrawler, NewsItem


class XCrawler(BaseCrawler):
    """基于 twitterapi.io 的 X 资讯采集。"""

    def __init__(self, config: dict, sources: List[dict]):
        super().__init__("X Crawler")
        self.config = config
        self.sources = sources
        self.session = requests.Session()
        self.session.headers.update(
            {
                "x-api-key": config["api_key"],
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            }
        )
        self.base_url = config["base_url"].rstrip("/")
        self.max_tweets_per_user = int(config.get("max_tweets_per_user", 5))
        self.timeout_seconds = int(config.get("timeout_seconds", 30))
        self.max_workers = int(config.get("max_workers", 8))
        self.retry_attempts = int(config.get("retry_attempts", 2))

    def crawl(self, hours: int = 24) -> List[NewsItem]:
        return self._crawl_sources_in_parallel(
            self.sources,
            self._crawl_single_source,
            hours,
            max_workers=self.max_workers,
        )

    def _crawl_single_source(self, source: dict, hours: int) -> List[NewsItem]:
        username = source.get("username") or source.get("author_handle") or str(source.get("name", "")).lstrip("@")
        if not username:
            raise ValueError("缺少 X 用户名")

        response = None
        for attempt in range(self.retry_attempts):
            try:
                response = requests.get(
                    f"{self.base_url}/twitter/user/last_tweets",
                    params={"userName": username},
                    headers=dict(self.session.headers),
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                break
            except requests.Timeout:
                if attempt == self.retry_attempts - 1:
                    return []
            except requests.RequestException:
                raise

        if response is None:
            return []

        payload = response.json()
        if payload.get("code") not in (0, None):
            raise ValueError(f"API 返回异常: {payload.get('msg') or payload}")

        tweets = (payload.get("data") or {}).get("tweets") or []
        items: List[NewsItem] = []

        for tweet in tweets:
            if self._should_skip_tweet(tweet):
                continue

            pub_time = self._parse_time(tweet)
            if not pub_time or not self._is_within_time_range(pub_time, hours):
                continue

            text = self._clean_text(tweet.get("text", ""))
            if not text:
                continue

            item = NewsItem(
                title=self._build_title(text),
                summary=text,
                url=self._resolve_url(tweet),
                source=source["source_name"],
                published_time=pub_time,
                content=text,
                image_url=self._extract_image_url(tweet),
                platform="x",
                source_type=source.get("source_type", "creator"),
                author_handle=username,
                source_url=source.get("source_url") or tweet.get("author", {}).get("url"),
                priority=source.get("priority", source.get("priority_hint", 1)),
            )
            items.append(item)

            if len(items) >= self.max_tweets_per_user:
                break

        return items

    def _should_skip_tweet(self, tweet: dict[str, Any]) -> bool:
        if tweet.get("isReply"):
            return True
        if tweet.get("retweeted_tweet"):
            return True
        text = (tweet.get("text") or "").strip()
        return not text

    def _parse_time(self, tweet: dict[str, Any]):
        created_at = tweet.get("createdAt")
        if not created_at:
            return None
        return date_parser.parse(created_at)

    def _resolve_url(self, tweet: dict[str, Any]) -> str:
        entities = tweet.get("entities") or {}
        for url_info in entities.get("urls") or []:
            expanded = (url_info.get("expanded_url") or "").strip()
            if expanded and "x.com/" not in expanded and "twitter.com/" not in expanded:
                return expanded
        return tweet.get("url") or tweet.get("twitterUrl") or ""

    def _build_title(self, text: str) -> str:
        title = text.split("\n", 1)[0].strip()
        if len(title) > 100:
            title = title[:97].rstrip() + "..."
        return title

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        return text

    def _extract_image_url(self, tweet: dict[str, Any]) -> str | None:
        media_list = (tweet.get("extendedEntities") or {}).get("media") or []
        for media in media_list:
            url = media.get("media_url_https") or media.get("media_url")
            if url:
                return url
        return None
