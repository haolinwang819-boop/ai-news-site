"""
Instagram 来源采集器。

使用 Instagram 公开的 web profile info 接口读取公开创作者资料和最近帖子。
"""
from __future__ import annotations

from typing import List

import requests
from datetime import datetime, timezone

from .base import BaseCrawler, NewsItem


class InstagramCrawler(BaseCrawler):
    PROFILE_API = "https://www.instagram.com/api/v1/users/web_profile_info/"

    def __init__(self, config: dict, sources: List[dict]):
        super().__init__("Instagram Crawler")
        self.config = config
        self.sources = sources
        self.timeout_seconds = int(config.get("timeout_seconds", 30))
        self.max_items_per_source = int(config.get("max_items_per_source", 3))
        self.max_workers = int(config.get("max_workers", 6))
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": config.get("user_agent", "Mozilla/5.0"),
                "x-ig-app-id": config.get("app_id", "936619743392459"),
                "Accept": "application/json",
                "Referer": "https://www.instagram.com/",
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
        username = source.get("author_handle") or source.get("name", "").lstrip("@")
        response = requests.get(
            self.PROFILE_API,
            params={"username": username},
            headers=dict(self.session.headers),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        user = ((response.json().get("data") or {}).get("user")) or {}
        timeline = ((user.get("edge_owner_to_timeline_media") or {}).get("edges")) or []
        items: List[NewsItem] = []

        for edge in timeline[: self.max_items_per_source]:
            node = edge.get("node") or {}
            taken_at = node.get("taken_at_timestamp")
            if not taken_at:
                continue
            published_time = datetime.fromtimestamp(int(taken_at), tz=timezone.utc)
            if not self._is_within_time_range(published_time, hours):
                continue

            shortcode = node.get("shortcode")
            caption_edges = ((node.get("edge_media_to_caption") or {}).get("edges")) or []
            caption = ""
            if caption_edges:
                caption = str((caption_edges[0].get("node") or {}).get("text") or "").strip()

            title = caption.split("\n", 1)[0].strip() if caption else f"{username} Instagram post"
            if len(title) > 100:
                title = title[:97].rstrip() + "..."

            post_type = "reel" if node.get("is_video") else "p"
            items.append(
                NewsItem(
                    title=title,
                    summary=caption[:220] if caption else title,
                    url=f"https://www.instagram.com/{post_type}/{shortcode}/",
                    source=source["source_name"],
                    published_time=published_time,
                    content=caption or title,
                    image_url=node.get("display_url"),
                    platform="instagram",
                    source_type=source.get("source_type", "creator"),
                    author_handle=username,
                    source_url=source.get("source_url") or f"https://www.instagram.com/{username}/",
                    priority=source.get("priority_hint", 2),
                )
            )

        return items
