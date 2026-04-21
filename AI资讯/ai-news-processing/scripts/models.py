"""
数据模型与图状态：PipelineItem、PipelineState，与规范一致。
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, TypedDict


@dataclass
class PipelineItem:
    """单条资讯，与「单条条目存储格式」一致。"""
    title: str
    url: str
    source: str
    published_time: str
    priority: int
    content: str
    image_url: Optional[str] = None
    logo_url: Optional[str] = None
    category: Optional[str] = None  # 分类节点之后才有
    platform: Optional[str] = None
    source_type: Optional[str] = None
    author_handle: Optional[str] = None
    source_url: Optional[str] = None
    product_rank: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "published_time": self.published_time,
            "priority": self.priority,
            "content": self.content,
            "image_url": self.image_url,
            "logo_url": self.logo_url,
        }
        if self.category is not None:
            d["category"] = self.category
        if self.platform is not None:
            d["platform"] = self.platform
        if self.source_type is not None:
            d["source_type"] = self.source_type
        if self.author_handle is not None:
            d["author_handle"] = self.author_handle
        if self.source_url is not None:
            d["source_url"] = self.source_url
        if self.product_rank is not None:
            d["product_rank"] = self.product_rank
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PipelineItem":
        return cls(
            title=str(d.get("title", "")),
            url=str(d.get("url", "")),
            source=str(d.get("source", "")),
            published_time=str(d.get("published_time", "")),
            priority=int(d.get("priority", 2)),
            content=str(d.get("content", "")),
            image_url=d.get("image_url") if d.get("image_url") else None,
            logo_url=d.get("logo_url") if d.get("logo_url") else None,
            category=d.get("category"),
            platform=d.get("platform") if d.get("platform") else None,
            source_type=d.get("source_type") if d.get("source_type") else None,
            author_handle=d.get("author_handle") if d.get("author_handle") else None,
            source_url=d.get("source_url") if d.get("source_url") else None,
            product_rank=int(d.get("product_rank")) if d.get("product_rank") is not None else None,
        )


def items_to_json_list(items: List[PipelineItem]) -> List[Dict[str, Any]]:
    """转为 JSON 可序列化的列表（每条 to_dict）。"""
    return [it.to_dict() for it in items]


def json_list_to_items(data: List[Dict[str, Any]]) -> List[PipelineItem]:
    """从 JSON 列表恢复 PipelineItem 列表。"""
    return [PipelineItem.from_dict(d) for d in data]


class PipelineState(TypedDict, total=False):
    """LangGraph 图状态：各节点读写这些键。"""
    input_items: List[Dict[str, Any]]
    normalized_items: List[PipelineItem]
    categorized_items: List[PipelineItem]
    deduped_items: List[PipelineItem]
    reflection_notes: Optional[Dict[str, Any]]
    iteration: int
    error: Optional[str]
