"""
Reddit 来源采集器。

当前只处理 allowlist 中的少量 seed 线程，使用公开 HTML 元数据提取标题和摘要。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .base import BaseCrawler, NewsItem


class RedditCrawler(BaseCrawler):
    def __init__(self, config: dict, sources: List[dict]):
        super().__init__("Reddit Crawler")
        self.config = config
        self.sources = sources
        self.timeout_seconds = int(config.get("timeout_seconds", 30))
        self.max_workers = int(config.get("max_workers", 2))
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": config.get("user_agent", "Mozilla/5.0 (compatible; ai-news-bot/0.1)"),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

    def crawl(self, hours: int = 24) -> List[NewsItem]:
        return self._crawl_sources_in_parallel(
            self.sources,
            self._crawl_single_source,
            hours,
            max_workers=self.max_workers,
        )

    def _crawl_single_source(self, source: dict, hours: int) -> List[NewsItem]:
        response = requests.get(
            source["source_url"],
            timeout=self.timeout_seconds,
            headers=dict(self.session.headers),
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        title = self._meta_content(soup, "og:title") or source["name"]
        description = self._meta_content(soup, "og:description") or title
        published = self._extract_time(soup)
        if not published:
            return []
        if not self._is_within_time_range(published, hours):
            return []

        return [
            NewsItem(
                title=title.strip(),
                summary=description.strip(),
                url=response.url,
                source=source["source_name"],
                published_time=published,
                content=description.strip(),
                image_url=self._meta_content(soup, "og:image"),
                platform="reddit",
                source_type=source.get("source_type", "community"),
                author_handle=None,
                source_url=source.get("source_url", response.url),
                priority=source.get("priority_hint", 3),
            )
        ]

    def _meta_content(self, soup: BeautifulSoup, prop: str) -> str | None:
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            return tag["content"].strip()
        return None

    def _extract_time(self, soup: BeautifulSoup) -> datetime | None:
        for tag in soup.find_all(["time", "faceplate-timeago"]):
            value = tag.get("datetime") or tag.get("ts")
            if not value:
                continue
            try:
                if value.isdigit():
                    return datetime.fromtimestamp(int(value), tz=timezone.utc)
                return date_parser.parse(value)
            except (TypeError, ValueError):
                continue
        return None
