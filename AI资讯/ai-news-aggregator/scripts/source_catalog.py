"""
Nexttoken 来源目录包装层。

供 config.py 和 crawler 使用，避免其它模块直接关心 DOCX 解析细节。
"""
from __future__ import annotations

from nexttoken_registry import get_all_sources, get_registry_counts, get_sources
from source_overrides import apply_source_overrides


def build_x_sources() -> list[dict]:
    return [dict(item) for item in get_sources("x")]


def build_instagram_sources() -> list[dict]:
    return [dict(item) for item in get_sources("instagram")]


def build_xiaohongshu_sources() -> list[dict]:
    return [dict(item) for item in get_sources("xiaohongshu")]


def build_wechat_sources() -> list[dict]:
    return [dict(item) for item in get_sources("wechat")]


def build_tool_sources() -> list[dict]:
    return [apply_source_overrides(dict(item)) for item in get_sources("tools")]


def build_news_sources() -> list[dict]:
    return [apply_source_overrides(dict(item)) for item in get_sources("news")]


def build_reddit_sources() -> list[dict]:
    return [dict(item) for item in get_sources("reddit")]


def build_all_sources() -> list[dict]:
    return [apply_source_overrides(dict(item)) for item in get_all_sources()]


def build_registry_counts() -> dict:
    return dict(get_registry_counts())
