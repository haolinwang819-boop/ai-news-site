"""
Nexttoken source registry.

Production reads the committed JSON snapshot so GitHub Actions does not need the
large local Word document. Local development can still rebuild that snapshot from
Nexttoken.docx when the document is available.
"""
from __future__ import annotations

import json
import os
import re
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List
from urllib.parse import urlparse
from xml.etree import ElementTree


REPO_ROOT = Path(__file__).resolve().parents[3]
JSON_PATH = REPO_ROOT / "data" / "nexttoken_sources.json"
DOCX_CANDIDATES = [
    Path(os.environ["NEXTTOKEN_DOCX_PATH"]).expanduser()
    if os.environ.get("NEXTTOKEN_DOCX_PATH")
    else None,
    REPO_ROOT / "Nexttoken.docx",
    REPO_ROOT / "_archive" / "Nexttoken.docx",
]
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

SECTION_HEADERS = {
    "x": {"x：", "x:"},
    "instagram": {"ins：", "ins:"},
    "xiaohongshu": {"小红书：", "小红书:"},
    "wechat": {"公众号 ：", "公众号：", "公众号 :", "公众号:"},
    "tools": {"ai工具 模型相关的网站：", "ai工具 模型相关的网站:"},
    "news": {"新闻网站 ：", "新闻网站：", "新闻网站 :", "新闻网站:"},
    "reddit": {"reddit 讨论帖 ：", "reddit 讨论帖：", "reddit 讨论帖 :", "reddit 讨论帖:"},
}

OFFICIAL_X_HANDLES = {
    "_inception_ai",
    "alibaba_qwen",
    "anthropicai",
    "cerebras",
    "claudeai",
    "deepseek_ai",
    "geminiapp",
    "googleai",
    "googledeepmind",
    "huggingface",
    "kimi_moonshot",
    "kwaiaicoder",
    "lmstudio",
    "manusai",
    "meta",
    "minimax_ai",
    "minmax_ai",
    "notebooklm",
    "openai",
    "openaidevs",
    "openrouterai",
    "perplexity_ai",
    "realcharai",
    "scale_ai",
    "tencentai_news",
    "vercel",
    "xai",
    "zai_org",
}

OFFICIAL_NEWS_NAMES = {
    "Amazon Science",
    "Apple Machine Learning",
    "DeepMind Blog",
    "Google AI Blog",
    "IBM Research Blog",
    "Microsoft Research Blog",
    "NVIDIA Blog",
    "OpenAI Blog",
}

RESEARCH_NEWS_NAMES = {
    "AAAI",
    "ACL",
    "ACM Digital Library",
    "Analytics Vidhya",
    "Apple Machine Learning",
    "arXiv",
    "CVPR",
    "Data Science Central",
    "GitHub Trending",
    "IBM Research Blog",
    "ICLR",
    "ICML",
    "IEEE Xplore",
    "Kaggle",
    "MIT News",
    "Microsoft Research Blog",
    "NeurIPS",
    "Towards Data Science",
}

WECHAT_MEDIA_NAMES = {
    "AIGC开放社区",
    "AI前线",
    "AI科技评论",
    "APPSO",
    "PlusAITech",
    "极客公园",
    "机器之心",
    "甲子光年",
    "量子位",
    "磐创AI",
    "硅星人Pro",
    "数字生命卡兹克",
    "第一新声",
    "新智元",
    "夕小瑶科技说",
    "暗涌Waves",
    "智东西",
}

IMAGE_PLACEHOLDERS = {"[image]", "image"}


def _read_docx_lines() -> List[str]:
    docx_path = next((path for path in DOCX_CANDIDATES if path and path.exists()), None)
    if docx_path is None:
        searched = ", ".join(str(path) for path in DOCX_CANDIDATES if path)
        raise FileNotFoundError(
            f"Nexttoken source registry not found. Expected {JSON_PATH} or one of: {searched}"
        )

    with zipfile.ZipFile(docx_path) as archive:
        document_xml = archive.read("word/document.xml")

    root = ElementTree.fromstring(document_xml)
    lines: List[str] = []
    for paragraph in root.findall(".//w:p", WORD_NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", WORD_NS))
        lines.append(text.replace("\xa0", " ").strip())
    return lines


def _read_json_registry() -> Dict[str, List[Dict[str, object]]]:
    with JSON_PATH.open("r", encoding="utf-8") as file:
        registry = json.load(file)

    return {
        section: list(registry.get(section, []))
        for section in SECTION_HEADERS
    }


def _normalize_header(line: str) -> str:
    return " ".join(line.strip().lower().split())


def _split_sections(lines: Iterable[str]) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {key: [] for key in SECTION_HEADERS}
    current_section: str | None = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if current_section:
                sections[current_section].append("")
            continue

        header = _normalize_header(line)
        matched = next((name for name, aliases in SECTION_HEADERS.items() if header in aliases), None)
        if matched:
            current_section = matched
            continue

        if current_section:
            sections[current_section].append(line)

    return sections


def _parse_numbered_records(lines: Iterable[str]) -> List[Dict[str, object]]:
    records: List[Dict[str, object]] = []
    index: int | None = None
    buffer: List[str] = []

    def flush():
        nonlocal index, buffer
        if index is None:
            return
        cleaned = [
            line.strip()
            for line in buffer
            if line.strip() and line.strip().lower() not in IMAGE_PLACEHOLDERS
        ]
        records.append({"index": index, "lines": cleaned})
        index = None
        buffer = []

    for raw_line in lines:
        line = raw_line.strip()
        if re.fullmatch(r"\d+", line):
            flush()
            index = int(line)
            continue
        if index is None:
            continue
        buffer.append(line)

    flush()
    return records


def _first_url(lines: Iterable[str]) -> str:
    for line in lines:
        if line.startswith("http://") or line.startswith("https://"):
            return line.strip()
    return ""


def _non_url_lines(lines: Iterable[str]) -> List[str]:
    return [line for line in lines if line and not line.startswith("http://") and not line.startswith("https://")]


def _instagram_handle(url: str) -> str:
    path = urlparse(url).path.strip("/")
    return path.split("/", 1)[0] if path else ""


def _x_handle(name: str, url: str) -> str:
    if name.startswith("@"):
        return name.lstrip("@")
    path = urlparse(url).path.strip("/")
    return path.split("/", 1)[0] if path else name


def _priority_from_source_type(source_type: str) -> int:
    if source_type == "official":
        return 0
    if source_type in {"media", "research"}:
        return 1
    if source_type == "creator":
        return 2
    return 3


def _build_x_source(record: Dict[str, object]) -> Dict[str, object] | None:
    lines = list(record["lines"])
    if not lines:
        return None

    name = _non_url_lines(lines)[0]
    url = _first_url(lines)
    remark_lines = [line for line in _non_url_lines(lines)[1:] if line]
    handle = _x_handle(name, url)
    normalized = handle.lower()
    source_type = "official" if normalized in OFFICIAL_X_HANDLES else "creator"

    return {
        "section": "x",
        "index": record["index"],
        "name": name,
        "url": url,
        "remark": " ".join(remark_lines).strip(),
        "source_name": f"@{handle} (X)",
        "source_url": url or f"https://x.com/{handle}",
        "platform": "x",
        "source_type": source_type,
        "crawl_method": "api",
        "auth_requirement": "x_api_key",
        "priority_hint": _priority_from_source_type(source_type),
        "author_handle": handle,
    }


def _build_instagram_source(record: Dict[str, object]) -> Dict[str, object] | None:
    lines = list(record["lines"])
    url = _first_url(lines)
    if not url:
        return None

    handle = _instagram_handle(url)
    name = f"@{handle}" if handle else f"Instagram {record['index']}"
    return {
        "section": "instagram",
        "index": record["index"],
        "name": name,
        "url": url,
        "remark": "",
        "source_name": name,
        "source_url": url,
        "platform": "instagram",
        "source_type": "creator",
        "crawl_method": "crawler",
        "auth_requirement": "instagram_cookie",
        "priority_hint": 2,
        "author_handle": handle or None,
    }


def _build_xhs_source(record: Dict[str, object]) -> Dict[str, object] | None:
    lines = list(record["lines"])
    text_lines = _non_url_lines(lines)
    url = _first_url(lines)
    if not text_lines or not url:
        return None

    name = text_lines[0]
    return {
        "section": "xiaohongshu",
        "index": record["index"],
        "name": name,
        "url": url,
        "remark": "",
        "source_name": name,
        "source_url": url,
        "platform": "xiaohongshu",
        "source_type": "creator",
        "crawl_method": "crawler",
        "auth_requirement": "xiaohongshu_cookie",
        "priority_hint": 2,
        "author_handle": None,
    }


def _build_wechat_source(record: Dict[str, object]) -> Dict[str, object] | None:
    lines = list(record["lines"])
    text_lines = _non_url_lines(lines)
    if not text_lines:
        return None

    name = text_lines[0]
    source_type = "media" if name in WECHAT_MEDIA_NAMES else "creator"
    return {
        "section": "wechat",
        "index": record["index"],
        "name": name,
        "url": "",
        "remark": "",
        "source_name": name,
        "source_url": "",
        "platform": "wechat",
        "source_type": source_type,
        "crawl_method": "manual_or_special_adapter",
        "auth_requirement": "special_adapter",
        "priority_hint": _priority_from_source_type(source_type),
        "author_handle": None,
    }


def _build_site_source(record: Dict[str, object], section: str) -> Dict[str, object] | None:
    lines = list(record["lines"])
    text_lines = _non_url_lines(lines)
    url = _first_url(lines)
    if not text_lines or not url:
        return None

    name = text_lines[0]
    if section == "tools":
        source_type = "official"
        platform = "site"
        crawl_method = "rss_or_html"
        auth_requirement = "none"
    else:
        if name in OFFICIAL_NEWS_NAMES:
            source_type = "official"
            platform = "site"
        elif name in RESEARCH_NEWS_NAMES:
            source_type = "research"
            platform = "research"
        else:
            source_type = "media"
            platform = "news"
        crawl_method = "rss_or_html"
        auth_requirement = "none"

    return {
        "section": section,
        "index": record["index"],
        "name": name,
        "url": url,
        "remark": "",
        "source_name": name,
        "source_url": url,
        "platform": platform,
        "source_type": source_type,
        "crawl_method": crawl_method,
        "auth_requirement": auth_requirement,
        "priority_hint": _priority_from_source_type(source_type),
        "author_handle": None,
    }


def _build_reddit_source(record: Dict[str, object]) -> Dict[str, object] | None:
    lines = list(record["lines"])
    text_lines = _non_url_lines(lines)
    url = _first_url(lines)
    if not text_lines or not url:
        return None

    title = text_lines[0]
    return {
        "section": "reddit",
        "index": record["index"],
        "name": title,
        "url": url,
        "remark": "",
        "source_name": "Reddit",
        "source_url": url,
        "platform": "reddit",
        "source_type": "community",
        "crawl_method": "html",
        "auth_requirement": "none",
        "priority_hint": 3,
        "author_handle": None,
    }


def _parse_section(section: str, lines: Iterable[str]) -> List[Dict[str, object]]:
    records = _parse_numbered_records(lines)
    builders = {
        "x": _build_x_source,
        "instagram": _build_instagram_source,
        "xiaohongshu": _build_xhs_source,
        "wechat": _build_wechat_source,
        "tools": lambda record: _build_site_source(record, "tools"),
        "news": lambda record: _build_site_source(record, "news"),
        "reddit": _build_reddit_source,
    }

    items: List[Dict[str, object]] = []
    for record in records:
        item = builders[section](record)
        if item is not None:
            items.append(item)
    return items


@lru_cache(maxsize=1)
def load_nexttoken_registry() -> Dict[str, List[Dict[str, object]]]:
    if JSON_PATH.exists():
        return _read_json_registry()

    sections = _split_sections(_read_docx_lines())
    return {name: _parse_section(name, section_lines) for name, section_lines in sections.items()}


def get_sources(section: str) -> List[Dict[str, object]]:
    return list(load_nexttoken_registry().get(section, []))


def get_all_sources() -> List[Dict[str, object]]:
    registry = load_nexttoken_registry()
    items: List[Dict[str, object]] = []
    for section in ("x", "instagram", "xiaohongshu", "wechat", "tools", "news", "reddit"):
        items.extend(registry.get(section, []))
    return items


def get_registry_counts() -> Dict[str, int]:
    registry = load_nexttoken_registry()
    return {section: len(items) for section, items in registry.items()}
