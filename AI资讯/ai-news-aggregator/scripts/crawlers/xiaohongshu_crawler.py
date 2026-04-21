"""
小红书来源采集器。

优先使用浏览器自动化读取登录态页面中的真实笔记链接；浏览器不可用时回退到 SSR
页面解析，至少保留近期卡片信息。
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, List
from urllib.parse import urlparse

import requests

from .base import BaseCrawler, NewsItem


class XiaohongshuCrawler(BaseCrawler):
    """使用已登录 cookie 抓取允许名单中的小红书创作者主页。"""

    def __init__(self, config: dict, sources: List[dict]):
        super().__init__("Xiaohongshu Crawler")
        self.config = config
        self.sources = sources
        self.timeout_seconds = int(config.get("timeout_seconds", 30))
        self.max_items_per_source = int(config.get("max_items_per_source", 3))
        self.wait_after_load_ms = int(config.get("wait_after_load_ms", 5000))
        self.use_browser = config.get("use_browser", True)
        self.browser_executable_path = config.get("browser_executable_path", "")

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": config.get("user_agent", "Mozilla/5.0"),
                "Cookie": config.get("cookie", ""),
                "Origin": config.get("origin", "https://www.xiaohongshu.com"),
                "Referer": config.get("referer", "https://www.xiaohongshu.com/"),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

    def crawl(self, hours: int = 24) -> List[NewsItem]:
        if not self.config.get("cookie"):
            print("⚠️ 小红书 cookie 未配置，跳过")
            return []

        items: List[NewsItem] = []
        playwright = browser = context = None

        if self.use_browser:
            try:
                playwright, browser, context = self._start_browser_context()
            except Exception as e:
                print(f"⚠️ 小红书浏览器模式不可用，回退 SSR: {e}")

        try:
            for source in self.sources:
                try:
                    if context is not None:
                        source_items = self._crawl_single_source_browser(context, source)
                    else:
                        source_items = self._crawl_single_source_http(source)
                    items.extend(source_items)
                    print(f"✓ {source['source_name']}: 获取 {len(source_items)} 条")
                except Exception as e:
                    print(f"✗ {source['source_name']}: 采集失败 - {e}")
        finally:
            if context is not None:
                context.close()
            if browser is not None:
                browser.close()
            if playwright is not None:
                playwright.stop()

        return items

    def _start_browser_context(self):
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()
        launch_kwargs = {"headless": True}
        if self.browser_executable_path:
            launch_kwargs["executable_path"] = self.browser_executable_path

        browser = playwright.chromium.launch(**launch_kwargs)
        context = browser.new_context(user_agent=self.config.get("user_agent", "Mozilla/5.0"))
        cookies = self._parse_cookie_header(self.config.get("cookie", ""))
        if cookies:
            context.add_cookies(cookies)
        return playwright, browser, context

    def _crawl_single_source_browser(self, context: Any, source: dict) -> List[NewsItem]:
        page = context.new_page()
        try:
            page.goto(
                source["source_url"],
                wait_until="domcontentloaded",
                timeout=self.timeout_seconds * 1000,
            )
            page.wait_for_timeout(self.wait_after_load_ms)

            cards = page.evaluate(
                """(maxItems) => {
                    const covers = Array.from(document.querySelectorAll('a.cover')).slice(0, maxItems);
                    return covers.map((cover) => {
                        const container = cover.parentElement;
                        const title = container?.querySelector('.footer a.title span')?.textContent?.trim() || '';
                        const author = container?.querySelector('.footer .author .name')?.textContent?.trim() || '';
                        const image = cover.querySelector('img')?.src || '';
                        const metaText = container?.querySelector('.footer')?.innerText || '';
                        return {
                            href: cover.href,
                            title,
                            author,
                            image,
                            metaText,
                        };
                    });
                }""",
                self.max_items_per_source,
            )
            profile_url = page.url.rstrip("/")
        finally:
            page.close()

        return self._cards_to_items(source, profile_url, cards)

    def _crawl_single_source_http(self, source: dict) -> List[NewsItem]:
        response = self.session.get(source["source_url"], allow_redirects=True, timeout=self.timeout_seconds)
        response.raise_for_status()

        state = self._extract_initial_state(response.text)
        note_groups = (((state.get("user") or {}).get("notes")) or [])
        note_wrappers = note_groups[0] if note_groups else []
        cards = []

        for wrapper in note_wrappers[: self.max_items_per_source]:
            note_card = wrapper.get("noteCard") or {}
            title = str(note_card.get("displayTitle") or "").strip()
            if not title:
                continue
            cover = note_card.get("cover") or {}
            image_url = cover.get("urlDefault") or cover.get("urlPre")
            cards.append(
                {
                    "href": "",
                    "title": title,
                    "author": source["source_name"],
                    "image": image_url,
                    "metaText": title,
                }
            )

        return self._cards_to_items(source, response.url.rstrip("/"), cards)

    def _cards_to_items(self, source: dict, profile_url: str, cards: List[dict]) -> List[NewsItem]:
        items: List[NewsItem] = []
        crawl_time = datetime.now(timezone.utc)

        for index, card in enumerate(cards):
            title = str(card.get("title") or "").strip()
            if not title:
                continue

            note_url = str(card.get("href") or "").strip()
            note_id = self._extract_note_id(note_url)
            published_time = self._parse_note_time(note_id) or crawl_time
            image_url = str(card.get("image") or "").strip() or None

            if not note_url:
                note_key = note_id or self._build_note_key(profile_url, title, index)
                note_url = self._build_note_url(profile_url, note_key)

            items.append(
                NewsItem(
                    title=title,
                    summary=title,
                    url=note_url,
                    source=source["source_name"],
                    published_time=published_time,
                    content=title,
                    image_url=image_url,
                    platform="xiaohongshu",
                    source_type=source.get("source_type", "creator"),
                    author_handle=(card.get("author") or source["source_name"]).strip(),
                    source_url=profile_url,
                    priority=source.get("priority_hint", 2),
                )
            )

        return items

    def _extract_initial_state(self, html: str) -> dict[str, Any]:
        match = re.search(r"window\.__INITIAL_STATE__=(\{.*?\})</script>", html)
        if not match:
            raise ValueError("未找到小红书页面状态")

        state_text = match.group(1)
        state_text = re.sub(r":undefined([,}])", r":null\1", state_text)
        state_text = re.sub(r":NaN([,}])", r":null\1", state_text)
        return json.loads(state_text)

    def _extract_note_id(self, note_url: str) -> str:
        path_parts = [part for part in urlparse(note_url).path.split("/") if part]
        if path_parts:
            candidate = path_parts[-1]
            if re.fullmatch(r"[0-9a-fA-F]{16,}", candidate):
                return candidate
        return ""

    def _parse_note_time(self, note_id: str) -> datetime | None:
        if not note_id or len(note_id) < 8:
            return None
        prefix = note_id[:8]
        if not re.fullmatch(r"[0-9a-fA-F]{8}", prefix):
            return None
        timestamp = int(prefix, 16)
        if not (1_500_000_000 <= timestamp <= 2_200_000_000):
            return None
        return datetime.fromtimestamp(timestamp, tz=timezone.utc)

    def _parse_cookie_header(self, raw_cookie: str) -> List[dict]:
        cookies: List[dict] = []
        for part in raw_cookie.split(";"):
            if "=" not in part:
                continue
            name, value = part.split("=", 1)
            name = name.strip()
            value = value.strip()
            if not name:
                continue
            cookies.append(
                {
                    "name": name,
                    "value": value,
                    "domain": ".xiaohongshu.com",
                    "path": "/",
                    "httpOnly": False,
                    "secure": True,
                    "sameSite": "Lax",
                }
            )
        return cookies

    def _build_note_key(self, profile_url: str, title: str, index: int) -> str:
        raw = f"{profile_url}|{index}|{title}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]

    def _build_note_url(self, profile_url: str, note_key: str) -> str:
        return f"{profile_url}#note-{note_key}"
