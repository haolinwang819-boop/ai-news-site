"""
爬虫模块初始化
"""
from .base import BaseCrawler, NewsItem
from .instagram_crawler import InstagramCrawler
from .product_hunt_crawler import ProductHuntCrawler
from .reddit_crawler import RedditCrawler
from .rss_crawler import RSSCrawler
from .site_crawler import SiteCrawler
from .wechat_crawler import WechatCrawler
from .x_crawler import XCrawler
from .xiaohongshu_crawler import XiaohongshuCrawler

__all__ = [
    "BaseCrawler",
    "NewsItem",
    "InstagramCrawler",
    "RSSCrawler",
    "RedditCrawler",
    "XCrawler",
    "ProductHuntCrawler",
    "SiteCrawler",
    "XiaohongshuCrawler",
    "WechatCrawler",
]
