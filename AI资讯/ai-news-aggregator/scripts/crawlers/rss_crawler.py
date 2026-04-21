"""
RSS源爬虫
"""
import feedparser
from datetime import datetime
from typing import List
import requests
from dateutil import parser as date_parser
from .base import BaseCrawler, NewsItem


class RSSCrawler(BaseCrawler):
    """RSS源爬虫"""
    
    def __init__(self, sources: List[dict], config: dict | None = None):
        """
        Args:
            sources: RSS源配置列表，每项包含 name, url, priority
        """
        super().__init__("RSS Crawler")
        self.sources = sources
        self.config = config or {}
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/rss+xml,application/xml,text/xml,*/*"})
        self.timeout_seconds = int(self.config.get("timeout_seconds", 20))
        self.max_workers = int(self.config.get("max_workers", 6))
    
    def crawl(self, hours: int = 24) -> List[NewsItem]:
        """采集所有RSS源"""
        return self._crawl_sources_in_parallel(
            self.sources,
            self._crawl_single_source,
            hours,
            source_label_key="name",
            max_workers=self.max_workers,
        )
    
    def _crawl_single_source(self, source: dict, hours: int) -> List[NewsItem]:
        """采集单个RSS源"""
        response = requests.get(
            source["url"],
            timeout=self.timeout_seconds,
            headers=dict(self.session.headers),
        )
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        items = []
        
        for entry in feed.entries:
            try:
                # 解析发布时间
                pub_time = self._parse_time(entry)
                if not pub_time or not self._is_within_time_range(pub_time, hours):
                    continue
                
                # 提取摘要
                summary = self._extract_summary(entry)
                
                item = NewsItem(
                    title=entry.get("title", "无标题"),
                    summary=summary,
                    url=entry.get("link", ""),
                    source=source["name"],
                    published_time=pub_time,
                    content=summary,
                    image_url=self._extract_image_url(entry),
                    platform=source.get("platform", "site"),
                    source_type=source.get("source_type", "media"),
                    source_url=source.get("source_url", source["url"]),
                    priority=source.get("priority", 2)
                )
                items.append(item)
                
            except Exception as e:
                print(f"  解析条目失败: {e}")
                continue
        
        return items
    
    def _parse_time(self, entry) -> datetime:
        """解析发布时间"""
        time_fields = ["published", "updated", "created"]
        
        for field in time_fields:
            if field in entry:
                try:
                    return date_parser.parse(entry[field])
                except:
                    continue
        
        # 如果没有时间字段，使用当前时间
        return datetime.now()
    
    def _extract_summary(self, entry) -> str:
        """提取摘要，限制长度"""
        summary = ""
        
        if "summary" in entry:
            summary = entry.summary
        elif "description" in entry:
            summary = entry.description
        elif "content" in entry:
            summary = entry.content[0].get("value", "")
        
        # 移除HTML标签（简单处理）
        import re
        summary = re.sub(r'<[^>]+>', '', summary)
        summary = summary.strip()
        
        # 限制长度
        if len(summary) > 200:
            summary = summary[:197] + "..."
        
        return summary

    def _extract_image_url(self, entry) -> str | None:
        """尽量提取配图 URL。"""
        media_content = entry.get("media_content") or []
        for media in media_content:
            url = media.get("url")
            if url:
                return url

        media_thumbnail = entry.get("media_thumbnail") or []
        for media in media_thumbnail:
            url = media.get("url")
            if url:
                return url

        links = entry.get("links") or []
        for link in links:
            if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("image/"):
                return link.get("href")

        return None
