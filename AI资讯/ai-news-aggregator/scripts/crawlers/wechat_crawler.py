"""
微信公众号采集器。

第一版使用搜狗微信文章搜索作为 mirrored/article-forward adapter。由于 Nexttoken
只给出账号名，没有 biz 或主页 URL，本实现按账号名搜索近期文章，并尽量用账号名
校验结果来源。
"""
from __future__ import annotations

import re
import time
from datetime import datetime
from typing import List
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from .base import BaseCrawler, NewsItem


class WechatCrawler(BaseCrawler):
    """通过搜狗微信搜索收集公众号近期文章。"""

    SEARCH_URL = "https://weixin.sogou.com/weixin"
    WEB_SEARCH_URL = "https://www.sogou.com/web"

    def __init__(self, config: dict, sources: List[dict]):
        super().__init__("Wechat Crawler")
        self.config = config
        self.sources = sources
        self.timeout_seconds = int(config.get("timeout_seconds", 30))
        self.max_items_per_source = int(config.get("max_items_per_source", 3))
        self.retry_attempts = int(config.get("retry_attempts", 3))
        self.max_workers = int(config.get("max_workers", 6))
        self.user_agent = config.get("user_agent", "Mozilla/5.0")

    def crawl(self, hours: int = 24) -> List[NewsItem]:
        return self._crawl_sources_in_parallel(
            self.sources,
            self._crawl_single_source,
            hours,
            max_workers=self.max_workers,
        )

    def _crawl_single_source(self, source: dict, hours: int) -> List[NewsItem]:
        search_url = f"{self.SEARCH_URL}?{urlencode({'type': 2, 'query': source['source_name']})}"
        response = self._search_with_retry(source["source_name"])

        soup = BeautifulSoup(response.text, "html.parser")
        items: List[NewsItem] = []
        expected_source = self._normalize_text(source["source_name"])

        for li in soup.select(".news-list li"):
            title_tag = li.select_one("h3 a")
            summary_tag = li.select_one("p.txt-info")
            if not title_tag or not summary_tag:
                continue

            title = " ".join(title_tag.get_text(" ", strip=True).split())
            summary = " ".join(summary_tag.get_text(" ", strip=True).split())
            result_source = self._extract_result_source(summary)

            if expected_source not in self._normalize_text(title):
                continue

            pub_time = self._extract_pub_time(li)
            if not pub_time:
                continue
            if not self._is_within_time_range(pub_time, hours):
                continue

            href = title_tag.get("href", "")
            url = f"https://weixin.sogou.com{href}" if href.startswith("/") else href
            image_url = None
            image_tag = li.select_one(".img-box img")
            if image_tag and image_tag.get("src"):
                image_url = image_tag["src"].strip()

            items.append(
                NewsItem(
                    title=title,
                    summary=summary,
                    url=url,
                    source=source["source_name"],
                    published_time=pub_time,
                    content=summary,
                    image_url=image_url,
                    platform="wechat",
                    source_type=source.get("source_type", "media"),
                    author_handle=result_source or None,
                    source_url=search_url,
                    priority=source.get("priority_hint", 1),
                )
            )

            if len(items) >= self.max_items_per_source:
                break

        if items:
            return items

        return self._crawl_web_search_fallback(source, hours)

    def _crawl_web_search_fallback(self, source: dict, hours: int) -> List[NewsItem]:
        query = f"{source['source_name']} 微信公众号"
        search_url = f"{self.WEB_SEARCH_URL}?{urlencode({'query': query})}"
        response = requests.get(
            self.WEB_SEARCH_URL,
            params={"query": query},
            timeout=self.timeout_seconds,
            headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        items: List[NewsItem] = []
        expected_source = self._normalize_text(source["source_name"])

        for node in soup.select(".vrwrap"):
            link_tag = node.select_one("a[href]")
            if not link_tag:
                continue

            href = (link_tag.get("href") or "").strip()
            title = " ".join(link_tag.get_text(" ", strip=True).split())
            block_text = " ".join(node.get_text(" ", strip=True).split())
            if expected_source not in self._normalize_text(block_text):
                continue

            if href.startswith("http://mp.weixin.qq.com") or href.startswith("https://mp.weixin.qq.com"):
                url = href
            elif "mp.weixin.qq.com" in block_text:
                url = href
            else:
                continue

            pub_time = self._extract_pub_time_from_text(block_text)
            if not pub_time:
                continue
            if not self._is_within_time_range(pub_time, hours):
                continue

            items.append(
                NewsItem(
                    title=title,
                    summary=block_text[:240],
                    url=url,
                    source=source["source_name"],
                    published_time=pub_time,
                    content=block_text[:240],
                    image_url=None,
                    platform="wechat",
                    source_type=source.get("source_type", "media"),
                    author_handle=None,
                    source_url=search_url,
                    priority=source.get("priority_hint", 1),
                )
            )

            if len(items) >= self.max_items_per_source:
                break

        return items

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://weixin.sogou.com/",
            }
        )
        return session

    def _search_with_retry(self, query: str) -> requests.Response:
        last_response = None
        for attempt in range(self.retry_attempts):
            session = self._build_session()
            response = session.get(self.SEARCH_URL, params={"type": 2, "query": query}, timeout=self.timeout_seconds)
            response.raise_for_status()
            if "antispider" not in response.url:
                return response
            last_response = response
            time.sleep(0.6 * (attempt + 1))

        if last_response is not None:
            return last_response
        raise RuntimeError("微信公众号搜索失败")

    def _extract_result_source(self, summary: str) -> str:
        match = re.search(r"公众号\s*([A-Za-z0-9_\-\u4e00-\u9fff]+?)(?=(今天|本周|昨日|[|，。,；;:：]|$))", summary)
        return match.group(1).strip() if match else ""

    def _extract_pub_time(self, li) -> datetime | None:
        script_text = " ".join(script.get_text(" ", strip=True) for script in li.select(".s-p script"))
        match = re.search(r"timeConvert\('(\d{10})'\)", script_text)
        if match:
            return datetime.fromtimestamp(int(match.group(1)))

        text = " ".join(li.select_one(".s-p").get_text(" ", strip=True).split()) if li.select_one(".s-p") else ""
        for token in text.split():
            try:
                return date_parser.parse(token)
            except (TypeError, ValueError):
                continue
        return None

    def _extract_pub_time_from_text(self, text: str) -> datetime | None:
        match = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)", text)
        if match:
            try:
                return date_parser.parse(match.group(1))
            except (TypeError, ValueError):
                return None
        match = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", text)
        if match:
            try:
                return date_parser.parse(match.group(1))
            except (TypeError, ValueError):
                return None
        return None

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"\s+", "", text or "").lower()
