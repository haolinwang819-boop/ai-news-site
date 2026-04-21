"""
通用站点采集器。

支持三类页面：
- feed / rss
- 新闻或博客列表页
- changelog / release notes 单页
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import List
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup, Tag
from dateutil import parser as date_parser

from .base import BaseCrawler, NewsItem


ARTICLE_HINTS = (
    "/20",
    "/article",
    "/announcement",
    "/blog",
    "/changelog",
    "/launch",
    "/news",
    "/post",
    "/release",
    "/research",
    "/update",
    "/updates",
)
BAD_FEED_PATTERNS = ("mailto:", "javascript:", "wp-json/oembed", "/oembed/", "privacy-policy", "feedback@")
COMMON_FEED_PATHS = (
    "/feed",
    "/feed/",
    "/rss",
    "/rss/",
    "/feed.xml",
    "/rss.xml",
    "/index.xml",
    "/blog/rss.xml",
    "/blog/feed",
    "/news/rss.xml",
)
GENERIC_TITLES = {
    "ai features",
    "browse",
    "company size",
    "discover",
    "explore",
    "filters",
    "learn",
    "on this page",
    "teams",
    "use cases",
    "what's new",
    "what’s new",
}


class SiteCrawler(BaseCrawler):
    """官网、新闻站、工具站通用采集器。"""

    def __init__(self, sources: List[dict], config: dict | None = None):
        super().__init__("Site Crawler")
        self.sources = sources
        self.config = config or {}
        self.timeout_seconds = int(self.config.get("timeout_seconds", 20))
        self.max_items_per_source = int(self.config.get("max_items_per_source", 3))
        self.max_workers = int(self.config.get("max_workers", 10))
        self.use_browser = self.config.get("use_browser", True)
        self.browser_executable_path = self.config.get(
            "browser_executable_path",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        )
        self.wait_after_load_ms = int(self.config.get("wait_after_load_ms", 3000))
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
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
        base_url = source.get("content_url") or source.get("source_url") or source.get("url")
        if not base_url:
            return []

        direct_feed_url = source.get("feed_url")
        page_mode = source.get("page_mode", "auto")
        last_error: Exception | None = None

        if direct_feed_url:
            try:
                feed_items = self._crawl_feed(source, direct_feed_url, hours)
                if feed_items or source.get("feed_only"):
                    return feed_items[: self.max_items_per_source]
            except requests.RequestException as exc:
                last_error = exc

        if page_mode == "changelog":
            try:
                changelog_items = self._crawl_changelog_page(source, base_url, hours)
                if changelog_items:
                    return changelog_items[: self.max_items_per_source]
            except requests.RequestException as exc:
                last_error = exc
        elif page_mode == "listing":
            try:
                listing_items = self._crawl_listing_page(source, base_url, hours)
                if listing_items:
                    return listing_items[: self.max_items_per_source]
            except requests.RequestException as exc:
                last_error = exc

        feed_url = None
        try:
            feed_url = self._discover_feed_url(source, base_url)
        except requests.RequestException as exc:
            last_error = exc
        if feed_url:
            try:
                feed_items = self._crawl_feed(source, feed_url, hours)
                if feed_items:
                    return feed_items[: self.max_items_per_source]
            except requests.RequestException as exc:
                last_error = exc

        try:
            fallback_items = self._crawl_listing_page(source, base_url, hours)
            return fallback_items[: self.max_items_per_source]
        except requests.RequestException as exc:
            last_error = exc

        if last_error is not None:
            raise last_error
        return []

    def _discover_feed_url(self, source: dict, base_url: str) -> str | None:
        soup, final_url = self._fetch_soup(source, base_url)
        parsed_base = urlparse(final_url)
        origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

        for tag in soup.find_all("link", href=True):
            rel = [part.lower() for part in (tag.get("rel") or [])]
            type_attr = str(tag.get("type") or "").lower()
            href = tag["href"].strip()
            if "alternate" not in rel:
                continue
            if not any(keyword in type_attr for keyword in ("rss", "atom", "xml")):
                continue
            candidate = urljoin(final_url, href)
            if self._is_valid_feed_candidate(candidate, origin):
                return candidate

        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            candidate = urljoin(final_url, href)
            if not self._is_valid_feed_candidate(candidate, origin):
                continue
            parsed_candidate = urlparse(candidate)
            path = parsed_candidate.path.lower()
            if not (
                path.endswith(".xml")
                or path.endswith("/feed")
                or path.endswith("/feed/")
                or path.endswith("/rss")
                or path.endswith("/rss/")
            ):
                continue
            return candidate

        for suffix in COMMON_FEED_PATHS:
            candidate = urljoin(origin, suffix)
            try:
                feed_response = self._get(candidate)
                if feed_response.ok and feed_response.text:
                    parsed_feed = feedparser.parse(feed_response.content)
                    if parsed_feed.entries:
                        return candidate
            except requests.RequestException:
                continue

        return None

    def _crawl_feed(self, source: dict, feed_url: str, hours: int) -> List[NewsItem]:
        response = self._get(feed_url)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        items: List[NewsItem] = []

        for entry in feed.entries:
            pub_time = self._parse_time(entry)
            if not pub_time or not self._is_within_time_range(pub_time, hours):
                continue

            title = str(entry.get("title") or "").strip()
            url = str(entry.get("link") or "").strip()
            if not title or not url:
                continue
            content = self._extract_summary(entry) or title
            if not self._matches_title_filters(source, f"{title} {content}"):
                continue

            items.append(
                NewsItem(
                    title=title,
                    summary=content,
                    url=url,
                    source=source["source_name"],
                    published_time=pub_time,
                    content=content,
                    image_url=self._extract_feed_image(entry),
                    platform=source.get("platform", "site"),
                    source_type=source.get("source_type", "official"),
                    source_url=source.get("content_url") or source.get("source_url", feed_url),
                    priority=source.get("priority_hint", 2),
                )
            )

        return items

    def _crawl_listing_page(self, source: dict, base_url: str, hours: int) -> List[NewsItem]:
        soup, final_url = self._fetch_soup(source, base_url)
        items = self._extract_timed_listing_items(soup, source, final_url, hours)
        if items:
            return items[: self.max_items_per_source]
        items = self._extract_linked_heading_items(soup, source, final_url, hours)
        if items:
            return items[: self.max_items_per_source]
        return self._crawl_homepage_links_from_soup(source, final_url, soup, hours)

    def _crawl_changelog_page(self, source: dict, base_url: str, hours: int) -> List[NewsItem]:
        soup, final_url = self._fetch_soup(source, base_url)
        items: List[NewsItem] = []
        current_date: datetime | None = None
        blocks = soup.find_all(["h2", "h3", "p", "li", "time"])
        waiting_for_first_entry = False

        index = 0
        while index < len(blocks):
            block = blocks[index]
            text = self._clean_text(block.get_text(" ", strip=True))
            if not text:
                index += 1
                continue

            parsed_date = self._parse_date_text(text)
            if parsed_date:
                current_date = parsed_date
                waiting_for_first_entry = True
                index += 1
                continue

            if not current_date or not self._is_within_time_range(current_date, hours):
                index += 1
                continue

            if block.name == "p":
                if not waiting_for_first_entry or text.lower().startswith("for more"):
                    index += 1
                    continue
                title = text
                summary = ""
                if index + 1 < len(blocks) and blocks[index + 1].name == "p":
                    summary = self._clean_text(blocks[index + 1].get_text(" ", strip=True))
                item = self._build_page_item(source, final_url, title, summary or title, current_date, block)
                if item:
                    items.append(item)
                    waiting_for_first_entry = False
            elif block.name == "h3" and not self._looks_like_date_heading(text):
                summary = self._extract_following_text(block)
                item = self._build_page_item(source, final_url, text, summary or text, current_date, block)
                if item:
                    items.append(item)
                    waiting_for_first_entry = False

            if len(items) >= self.max_items_per_source:
                break
            index += 1

        return items

    def _extract_timed_listing_items(self, soup: BeautifulSoup, source: dict, base_url: str, hours: int) -> List[NewsItem]:
        items: List[NewsItem] = []
        seen_urls: set[str] = set()

        for time_tag in soup.find_all("time"):
            published_time = self._parse_date_text(
                time_tag.get("datetime") or time_tag.get_text(" ", strip=True)
            )
            if not published_time or not self._is_within_time_range(published_time, hours):
                continue

            title_tag = self._find_nearest_title_tag(time_tag)
            if title_tag is None:
                continue
            title = self._clean_text(title_tag.get_text(" ", strip=True))
            if not self._is_valid_title(title):
                continue
            if not self._matches_title_filters(source, title):
                continue

            link = title_tag.find("a", href=True) or title_tag.parent.find("a", href=True)
            item_url = urljoin(base_url, link["href"].strip()) if link else self._fragment_url(base_url, title_tag, title)
            if item_url in seen_urls:
                continue

            summary = self._extract_following_text(title_tag) or self._extract_following_text(time_tag) or title
            items.append(
                NewsItem(
                    title=title[:120],
                    summary=summary[:280],
                    url=item_url,
                    source=source["source_name"],
                    published_time=published_time,
                    content=summary[:280],
                    image_url=self._extract_page_image(soup, base_url),
                    platform=source.get("platform", "site"),
                    source_type=source.get("source_type", "official"),
                    source_url=source.get("content_url") or source.get("source_url", base_url),
                    priority=source.get("priority_hint", 2),
                )
            )
            seen_urls.add(item_url)
            if len(items) >= self.max_items_per_source:
                break

        return items

    def _extract_linked_heading_items(self, soup: BeautifulSoup, source: dict, base_url: str, hours: int) -> List[NewsItem]:
        items: List[NewsItem] = []
        seen_urls: set[str] = set()
        base_netloc = urlparse(base_url).netloc

        for tag in soup.find_all(["h2", "h3", "h4"]):
            title = self._clean_text(tag.get_text(" ", strip=True))
            if not self._is_valid_title(title):
                continue
            if not self._matches_title_filters(source, title):
                continue

            link = tag.find("a", href=True) or tag.parent.find("a", href=True)
            if link is None:
                continue

            href = urljoin(base_url, link["href"].strip())
            parsed_href = urlparse(href)
            if parsed_href.scheme not in {"http", "https"}:
                continue
            if parsed_href.netloc and parsed_href.netloc != base_netloc:
                continue
            if href in seen_urls or href == base_url:
                continue

            article_item = self._fetch_article_candidate(source, href, title, hours)
            if article_item is None:
                continue

            items.append(article_item)
            seen_urls.add(href)
            if len(items) >= self.max_items_per_source:
                break

        return items

    def _crawl_homepage_links_from_soup(self, source: dict, base_url: str, soup: BeautifulSoup, hours: int) -> List[NewsItem]:
        base_netloc = urlparse(base_url).netloc
        seen_urls: set[str] = set()
        candidates: list[tuple[str, str]] = []

        for tag in soup.find_all("a", href=True):
            raw_href = tag["href"].strip()
            if raw_href.startswith(BAD_FEED_PATTERNS):
                continue
            href = urljoin(base_url, raw_href)
            parsed_href = urlparse(href)
            title = self._clean_text(tag.get_text(" ", strip=True))
            if not href or not title:
                continue
            if parsed_href.scheme not in {"http", "https"}:
                continue
            if parsed_href.netloc and parsed_href.netloc != base_netloc:
                continue
            if href in seen_urls:
                continue
            if not any(hint in href.lower() for hint in ARTICLE_HINTS):
                continue
            if len(title) < 8:
                continue
            if not self._matches_title_filters(source, title):
                continue

            seen_urls.add(href)
            candidates.append((href, title))
            if len(candidates) >= max(self.max_items_per_source * 5, self.max_items_per_source):
                break

        items: List[NewsItem] = []
        for href, fallback_title in candidates:
            article_item = self._fetch_article_candidate(source, href, fallback_title, hours)
            if article_item is None:
                continue
            items.append(article_item)
            if len(items) >= self.max_items_per_source:
                break

        return items

    def _fetch_article_candidate(self, source: dict, article_url: str, fallback_title: str, hours: int) -> NewsItem | None:
        try:
            response = self._get(article_url)
            response.raise_for_status()
        except requests.RequestException:
            return None
        soup = BeautifulSoup(response.text, "html.parser")

        published_time = self._extract_article_time(soup, article_url)
        if not published_time or not self._is_within_time_range(published_time, hours):
            return None

        title = (
            self._meta_content(soup, "og:title")
            or self._meta_content(soup, "twitter:title")
            or fallback_title
        ).strip()
        summary = self._extract_article_summary(soup, fallback_title)
        image_url = self._extract_page_image(soup, article_url)

        return NewsItem(
            title=title[:120],
            summary=summary,
            url=article_url,
            source=source["source_name"],
            published_time=published_time,
            content=summary,
            image_url=image_url,
            platform=source.get("platform", "site"),
            source_type=source.get("source_type", "official"),
            source_url=source.get("content_url") or source.get("source_url", article_url),
            priority=source.get("priority_hint", 2),
        )

    def _fetch_soup(self, source: dict, url: str) -> tuple[BeautifulSoup, str]:
        allow_browser = self.use_browser and bool(source.get("browser_fallback") or source.get("prefer_browser"))
        if self.use_browser and source.get("prefer_browser"):
            html_text, final_url = self._get_html_with_browser(url)
            return BeautifulSoup(html_text, "html.parser"), final_url
        try:
            response = self._get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser"), response.url
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else None
            if allow_browser and status_code in {401, 403, 405, 406, 412, 418, 429}:
                html_text, final_url = self._get_html_with_browser(url)
                return BeautifulSoup(html_text, "html.parser"), final_url
            raise
        except requests.RequestException:
            if allow_browser:
                html_text, final_url = self._get_html_with_browser(url)
                return BeautifulSoup(html_text, "html.parser"), final_url
            raise

    def _get_html_with_browser(self, url: str) -> tuple[str, str]:
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()
        launch_kwargs = {"headless": True}
        if self.browser_executable_path:
            launch_kwargs["executable_path"] = self.browser_executable_path

        browser = playwright.chromium.launch(**launch_kwargs)
        page = browser.new_page(user_agent=self.session.headers.get("User-Agent", "Mozilla/5.0"))
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_seconds * 1000)
            page.wait_for_timeout(self.wait_after_load_ms)
            return page.content(), page.url
        finally:
            page.close()
            browser.close()
            playwright.stop()

    def _is_valid_feed_candidate(self, candidate: str, origin: str) -> bool:
        lowered = candidate.lower()
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"}:
            return False
        if any(pattern in lowered for pattern in BAD_FEED_PATTERNS):
            return False
        if not candidate.startswith(origin):
            return False
        return True

    def _find_nearest_title_tag(self, time_tag: Tag) -> Tag | None:
        parent = time_tag.parent if isinstance(time_tag.parent, Tag) else None
        if parent is not None:
            siblings = list(parent.children)
            try:
                index = siblings.index(time_tag)
            except ValueError:
                index = -1
            if index >= 0:
                for sibling in reversed(siblings[:index]):
                    if isinstance(sibling, Tag) and sibling.name in {"h1", "h2", "h3", "h4"}:
                        if self._is_valid_title(self._clean_text(sibling.get_text(" ", strip=True))):
                            return sibling
                for sibling in siblings[index + 1 :]:
                    if isinstance(sibling, Tag) and sibling.name in {"h1", "h2", "h3", "h4"}:
                        if self._is_valid_title(self._clean_text(sibling.get_text(" ", strip=True))):
                            return sibling

        current = time_tag.parent
        while current is not None:
            heading = current.find(["h1", "h2", "h3", "h4"])
            if heading is not None and self._is_valid_title(self._clean_text(heading.get_text(" ", strip=True))):
                return heading
            current = current.parent if isinstance(current.parent, Tag) else None

        for sibling in list(time_tag.previous_elements):
            if isinstance(sibling, Tag) and sibling.name in {"h1", "h2", "h3", "h4"}:
                return sibling
        return None

    def _build_page_item(
        self,
        source: dict,
        base_url: str,
        title: str,
        summary: str,
        published_time: datetime,
        node: Tag,
    ) -> NewsItem | None:
        cleaned_title = self._clean_text(title)
        if not self._is_valid_title(cleaned_title):
            return None
        return NewsItem(
            title=cleaned_title[:120],
            summary=summary[:280],
            url=self._fragment_url(base_url, node, cleaned_title),
            source=source["source_name"],
            published_time=published_time,
            content=summary[:280],
            image_url=None,
            platform=source.get("platform", "site"),
            source_type=source.get("source_type", "official"),
            source_url=source.get("content_url") or source.get("source_url", base_url),
            priority=source.get("priority_hint", 2),
        )

    def _fragment_url(self, base_url: str, node: Tag, title: str) -> str:
        element_id = node.get("id") or node.parent.get("id") if isinstance(node.parent, Tag) else None
        if element_id:
            return f"{base_url}#{element_id}"
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
        return f"{base_url}#{slug}" if slug else base_url

    def _extract_following_text(self, node: Tag) -> str:
        for sibling in node.next_siblings:
            if not isinstance(sibling, Tag):
                continue
            if sibling.name in {"h1", "h2", "h3", "h4", "time"}:
                return ""
            text = self._clean_text(sibling.get_text(" ", strip=True))
            if text:
                return text[:280]
        return ""

    def _parse_time(self, entry):
        for field in ("published", "updated", "created"):
            value = entry.get(field)
            if not value:
                continue
            try:
                return date_parser.parse(value)
            except (TypeError, ValueError):
                continue
        return None

    def _parse_date_text(self, text: str) -> datetime | None:
        cleaned = self._clean_text(text)
        if not cleaned:
            return None
        normalized = cleaned.replace("Date:", "").replace("[", "").replace("]", "").strip()
        try:
            parsed = date_parser.parse(normalized, fuzzy=True)
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed.year < 2020:
            return None
        return parsed

    def _looks_like_date_heading(self, text: str) -> bool:
        return self._parse_date_text(text) is not None

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    def _is_valid_title(self, title: str) -> bool:
        lowered = title.lower()
        month_hits = sum(lowered.count(month) for month in ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"))
        if len(title) < 8 or len(title) > 180:
            return False
        if lowered in GENERIC_TITLES:
            return False
        if re.fullmatch(r"(jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)(\s+\w+){0,3}\s+\d{4}", lowered):
            return False
        if month_hits >= 2 and re.search(r"\b20\d{2}\b", lowered) and len(title.split()) <= 8:
            return False
        if self._looks_like_date_heading(title):
            return False
        return True

    def _matches_title_filters(self, source: dict, title: str) -> bool:
        filters = source.get("title_filters") or []
        if not filters:
            return True
        lowered = title.lower()
        return any(keyword.lower() in lowered for keyword in filters)

    def _extract_summary(self, entry) -> str:
        raw = ""
        if entry.get("summary"):
            raw = entry.get("summary", "")
        elif entry.get("description"):
            raw = entry.get("description", "")
        elif entry.get("content"):
            raw = entry["content"][0].get("value", "")

        clean = re.sub(r"<[^>]+>", "", raw).strip()
        if len(clean) > 280:
            return clean[:277] + "..."
        return clean

    def _extract_feed_image(self, entry) -> str | None:
        for media in entry.get("media_content") or []:
            url = media.get("url")
            if url:
                return url

        for media in entry.get("media_thumbnail") or []:
            url = media.get("url")
            if url:
                return url

        return None

    def _extract_page_image(self, soup: BeautifulSoup, base_url: str) -> str | None:
        tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if tag and tag.get("content"):
            return urljoin(base_url, tag["content"].strip())
        return None

    def _get(self, url: str) -> requests.Response:
        return requests.get(url, timeout=self.timeout_seconds, headers=dict(self.session.headers))

    def _meta_content(self, soup: BeautifulSoup, prop: str) -> str | None:
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        if tag and tag.get("content"):
            return str(tag["content"]).strip()
        return None

    def _extract_article_summary(self, soup: BeautifulSoup, fallback_title: str) -> str:
        summary = (
            self._meta_content(soup, "description")
            or self._meta_content(soup, "og:description")
            or self._meta_content(soup, "twitter:description")
            or fallback_title
        )
        summary = self._clean_text(summary or "")
        if len(summary) > 280:
            return summary[:277] + "..."
        return summary

    def _extract_article_time(self, soup: BeautifulSoup, article_url: str) -> datetime | None:
        for key in (
            "article:published_time",
            "article:modified_time",
            "og:updated_time",
            "publish-date",
            "date",
        ):
            value = self._meta_content(soup, key)
            if value:
                try:
                    return date_parser.parse(value)
                except (TypeError, ValueError):
                    pass

        for tag in soup.find_all("time"):
            value = tag.get("datetime") or tag.get_text(" ", strip=True)
            if not value:
                continue
            try:
                return date_parser.parse(value)
            except (TypeError, ValueError):
                continue

        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            text = script.string or script.get_text(" ", strip=True)
            if not text:
                continue
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                continue
            published = self._find_jsonld_date(data)
            if published:
                return published

        match = re.search(r"/(20\d{2})/(0?[1-9]|1[0-2])/(0?[1-9]|[12]\d|3[01])/", article_url)
        if match:
            try:
                return date_parser.parse("-".join(match.groups()))
            except (TypeError, ValueError):
                return None
        return None

    def _find_jsonld_date(self, data) -> datetime | None:
        if isinstance(data, list):
            for item in data:
                value = self._find_jsonld_date(item)
                if value:
                    return value
            return None

        if not isinstance(data, dict):
            return None

        for key in ("datePublished", "dateCreated", "dateModified"):
            value = data.get(key)
            if value:
                try:
                    return date_parser.parse(value)
                except (TypeError, ValueError):
                    continue

        for nested_key in ("mainEntity", "itemListElement", "@graph"):
            nested = data.get(nested_key)
            value = self._find_jsonld_date(nested)
            if value:
                return value
        return None
