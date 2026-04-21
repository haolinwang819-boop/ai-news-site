"""
数据处理器：去重、分类、排序
"""
import re
from typing import List, Dict
from difflib import SequenceMatcher
from crawlers.base import NewsItem


# 分类关键词配置
CATEGORY_KEYWORDS = {
    "image_video": [
        "runway", "hailuo", "海螺", "minimax", "kling", "可灵", "seedream", 
        "qwen", "glm", "hunyuan", "tencent", "bytedance", "midjourney", "mj", 
        "google", "nanobanana", "veo", "gemini", "gpt", "wan", "imagen", 
        "stable diffusion", "sd", "miracle", "chatgpt", "flux", "z-image", 
        "vidu", "qwen-image", "grok-image", "grok-video", "adobe firefly", 
        "lumal", "meta", "pika", "chatgpt-sora", "sora", "liblib", "pixverse", 
        "清影", "qingying", "ai生视频", "luma ray", "seedance", "mochi", "motion", 
        "jimeng", "即梦", "dall-e", "dalle", "video generation", "image generation", 
        "text-to-image", "text-to-video", "图像生成", "视频生成", "ai绘画", "ai作图"
    ],
    "llm": [
        "deepseek", "chatgpt", "grok", "gemini", "豆包", "doubao", "qwen", 
        "kimi", "minimax", "文心", "ernie", "claude", "meta", "longcat", 
        "glm", "mistral", "mimo", "amazon", "百川", "baichuan", "商汤", 
        "sensetime", "天工", "tiangong", "seed", "gpt-4", "gpt-5", "openai", 
        "anthropic", "llama", "大语言模型", "llm", "大模型", "foundation model", 
        "o1", "o3", "reasoning model"
    ],
    "startup": [
        "launch", "发布", "beta", "新品", "startup", "融资",
        "seed round", "series a", "series b", "获投",
        "producthunt", "product hunt"
    ]
}

# 优先级关键词
PRIORITY_KEYWORDS = {
    0: ["release", "launch", "发布", "重磅", "major update", "重大更新", "officially"],
    1: ["billion", "亿", "regulation", "breakthrough", "突破", "法规", "政策"],
}


class DataProcessor:
    """数据处理器"""
    
    def __init__(self):
        self.seen_urls = set()
        self.seen_titles = []
    
    def process(self, items: List[NewsItem]) -> Dict[str, List[NewsItem]]:
        """
        处理资讯列表：去重、分类、排序
        
        Returns:
            按分类组织的资讯字典
        """
        # 1. 去重
        unique_items = self._deduplicate(items)
        print(f"\n去重后: {len(unique_items)} 条（原 {len(items)} 条）")
        
        # 2. 分类
        for item in unique_items:
            item.category = self._classify(item)
            item.priority = self._calculate_priority(item)
        
        # 3. 按分类组织
        categorized = {
            "image_video": [],
            "llm": [],
            "startup": [],
            "hot_news": []
        }
        
        for item in unique_items:
            category = item.category
            if category not in categorized:
                category = "hot_news"
            categorized[category].append(item)
        
        # 4. 每个分类内按优先级排序
        for category in categorized:
            categorized[category].sort(key=lambda x: (x.priority, -x.published_time.timestamp()))
        
        # 打印统计
        print("\n分类统计:")
        print(f"  🎨 图视频: {len(categorized['image_video'])} 条")
        print(f"  🤖 大模型: {len(categorized['llm'])} 条")
        print(f"  🚀 黑马新品: {len(categorized['startup'])} 条")
        print(f"  🔥 热点资讯: {len(categorized['hot_news'])} 条")
        
        return categorized
    
    def _deduplicate(self, items: List[NewsItem]) -> List[NewsItem]:
        """去重：基于URL和标题相似度"""
        unique = []
        
        for item in items:
            # URL去重
            if item.url in self.seen_urls:
                continue
            
            # 标题相似度去重
            is_duplicate = False
            for seen_title in self.seen_titles:
                similarity = SequenceMatcher(None, item.title.lower(), seen_title.lower()).ratio()
                if similarity > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                self.seen_urls.add(item.url)
                self.seen_titles.append(item.title)
                unique.append(item)
        
        return unique
    
    def _classify(self, item: NewsItem) -> str:
        """根据关键词分类"""
        text = (item.title + " " + item.summary).lower()
        
        # 按顺序检查各分类
        for category, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    return category
        
        return "hot_news"
    
    def _calculate_priority(self, item: NewsItem) -> int:
        """计算优先级"""
        text = (item.title + " " + item.summary).lower()
        
        for priority, keywords in PRIORITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    return priority
        
        return item.priority  # 保持来源默认优先级
