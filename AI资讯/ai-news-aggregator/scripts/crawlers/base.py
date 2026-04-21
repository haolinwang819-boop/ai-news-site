"""
爬虫基类和通用工具
"""
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional


@dataclass
class NewsItem:
    """资讯条目数据结构"""
    title: str
    summary: str
    url: str
    source: str
    published_time: datetime
    content: Optional[str] = None
    image_url: Optional[str] = None
    logo_url: Optional[str] = None
    platform: Optional[str] = None
    source_type: Optional[str] = None
    author_handle: Optional[str] = None
    source_url: Optional[str] = None
    product_rank: Optional[int] = None
    category: str = "hot_news"  # image_video, llm, startup, hot_news
    priority: int = 2  # 0=P0重磅, 1=P1重要, 2=P2日常, 3=P3其他
    
    def to_dict(self):
        return {
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "source": self.source,
            "published_time": self.published_time.isoformat(),
            "content": self.content if self.content is not None else self.summary,
            "image_url": self.image_url,
            "logo_url": self.logo_url,
            "platform": self.platform,
            "source_type": self.source_type,
            "author_handle": self.author_handle,
            "source_url": self.source_url,
            "product_rank": self.product_rank,
            "category": self.category,
            "priority": self.priority
        }


class BaseCrawler(ABC):
    """爬虫基类"""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def crawl(self, hours: int = 200) -> List[NewsItem]:
        """
        采集指定时间范围内的资讯
        
        Args:
            hours: 采集过去多少小时的内容
            
        Returns:
            资讯列表
        """
        pass
    
    def _is_within_time_range(self, pub_time: datetime, hours: int) -> bool:
        """检查发布时间是否在指定范围内"""
        now = datetime.now(pub_time.tzinfo) if pub_time.tzinfo else datetime.now()
        delta = now - pub_time
        return delta.total_seconds() <= hours * 3600

    def _crawl_sources_in_parallel(
        self,
        sources: List[dict],
        crawl_fn: Callable[[dict, int], List[NewsItem]],
        hours: int,
        source_label_key: str = "source_name",
        max_workers: int = 1,
    ) -> List[NewsItem]:
        """并发抓取多个来源，保留逐来源日志。"""
        if max_workers <= 1 or len(sources) <= 1:
            items: List[NewsItem] = []
            for source in sources:
                try:
                    source_items = crawl_fn(source, hours)
                    items.extend(source_items)
                    print(f"✓ {source.get(source_label_key, self.name)}: 获取 {len(source_items)} 条")
                except Exception as e:
                    print(f"✗ {source.get(source_label_key, self.name)}: 采集失败 - {e}")
            return items

        items: List[NewsItem] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(crawl_fn, source, hours): source
                for source in sources
            }
            for future in as_completed(future_map):
                source = future_map[future]
                label = source.get(source_label_key, self.name)
                try:
                    source_items = future.result()
                    items.extend(source_items)
                    print(f"✓ {label}: 获取 {len(source_items)} 条")
                except Exception as e:
                    print(f"✗ {label}: 采集失败 - {e}")
        return items
