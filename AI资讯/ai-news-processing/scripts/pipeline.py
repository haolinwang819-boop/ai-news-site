"""
LangGraph 图与四个节点：标准化、分类、去重、反思。节点 + 图构建 + ProcessingPipeline。
"""
import json
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List

from langgraph.graph import END, START, StateGraph

from .config import MAX_REFLECTION_ITERATIONS
from .llm_utils import PromptLoader, get_llm_invoker, parse_json_from_model_output
from .models import (
    PipelineItem,
    PipelineState,
    items_to_json_list,
    json_list_to_items,
)


IMAGE_VIDEO_KEYWORDS = (
    "adobe firefly",
    "dall-e",
    "image generation",
    "jimeng",
    "kling",
    "midjourney",
    "runway",
    "sora",
    "stable diffusion",
    "vidu",
    "video generation",
    "即梦",
    "可灵",
)

LLM_KEYWORDS = (
    "anthropic",
    "chatgpt",
    "claude",
    "deepseek",
    "gemini",
    "glm",
    "gpt",
    "kimi",
    "llama",
    "mistral",
    "openai",
    "perplexity",
    "qwen",
    "豆包",
    "通义千问",
)

STARTUP_KEYWORDS = (
    "beta",
    "device",
    "display",
    "funding",
    "launch",
    "launches",
    "launched",
    "platform",
    "product hunt",
    "producthunt",
    "seed round",
    "series a",
    "series b",
    "startup",
    "smart home",
    "tool",
    "tools",
    "update",
    "发布",
    "融资",
)

AI_SIGNAL_KEYWORDS = (
    "ai",
    "ai-powered",
    "agent",
    "agents",
    "artificial intelligence",
    "assistant",
    "automation",
    "claude",
    "copilot",
    "deep learning",
    "developer api",
    "developer apis",
    "foundation model",
    "generative ai",
    "gemini",
    "gpt",
    "llm",
    "machine learning",
    "model",
    "models",
    "neural network",
    "openai",
    "prompt",
    "siri",
    "智能",
    "模型",
    "生成式",
    "人工智能",
)

STARTUP_PLATFORM_KEYWORDS = (
    "api",
    "apis",
    "app",
    "apps",
    "cli",
    "customer experience",
    "customer service",
    "developer",
    "developers",
    "ecosystem",
    "healthcare",
    "platform",
    "product",
    "products",
    "sdk",
    "stack",
    "studio",
    "tool",
    "tools",
    "workspace",
)

HOT_NEWS_KEYWORDS = (
    "acquisition",
    "collaboration",
    "delay",
    "delayed",
    "industry",
    "lawsuit",
    "partnership",
    "policy",
    "regulation",
    "report",
    "research",
    "science",
    "strategy",
    "trend",
)


def _run_prompt(prompt_loader: Any, invoker: Callable[[str], str], prompt_name: str, input_json: str) -> str:
    prompt = prompt_loader.load(prompt_name, input_json=input_json)
    return invoker(prompt)


def _fallback_normalize_items(input_list: List[Dict[str, Any]]) -> List[PipelineItem]:
    now_iso = datetime.now(timezone.utc).isoformat()
    items: List[PipelineItem] = []

    for raw in input_list:
        title = str(raw.get("title") or "").strip()
        url = str(raw.get("url") or "").strip()
        source = str(raw.get("source") or "").strip()
        content = str(raw.get("content") or raw.get("summary") or title).strip()
        if not title or not url or not source or not content:
            continue

        try:
            priority = int(raw.get("priority", 2))
        except (TypeError, ValueError):
            priority = 2

        items.append(
            PipelineItem(
                title=title,
                url=url,
                source=source,
                published_time=str(raw.get("published_time") or now_iso),
                priority=priority,
                content=content,
                image_url=raw.get("image_url") if raw.get("image_url") else None,
                logo_url=raw.get("logo_url") if raw.get("logo_url") else None,
                category=raw.get("category"),
                platform=raw.get("platform") if raw.get("platform") else None,
                source_type=raw.get("source_type") if raw.get("source_type") else None,
                author_handle=raw.get("author_handle") if raw.get("author_handle") else None,
                source_url=raw.get("source_url") if raw.get("source_url") else None,
                product_rank=int(raw.get("product_rank")) if raw.get("product_rank") is not None else None,
            )
        )

    return items


def _contains_keyword(text: str, keyword: str) -> bool:
    lowered = text.lower()
    token = keyword.lower()
    if re.search(r"[\u4e00-\u9fff]", token):
        return token in lowered
    pattern = re.compile(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])")
    return bool(pattern.search(lowered))


def _keyword_score(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for keyword in keywords if _contains_keyword(text, keyword))


def _classify_item(item: PipelineItem) -> str:
    text = " ".join(
        part for part in (
            item.title,
            item.content,
            item.source,
            item.url,
            item.platform or "",
            item.source_type or "",
        ) if part
    ).lower()

    image_score = _keyword_score(text, IMAGE_VIDEO_KEYWORDS)
    llm_score = _keyword_score(text, LLM_KEYWORDS)
    startup_score = _keyword_score(text, STARTUP_KEYWORDS)
    ai_signal_score = image_score + llm_score + _keyword_score(text, AI_SIGNAL_KEYWORDS)
    platform_score = _keyword_score(text, STARTUP_PLATFORM_KEYWORDS)
    hot_news_score = _keyword_score(text, HOT_NEWS_KEYWORDS)

    if platform_score >= 2 and ai_signal_score > 0:
        startup_score += 2
    elif platform_score >= 1 and ai_signal_score > 0:
        startup_score += 1

    if _contains_keyword(text, "smart home") or _contains_keyword(text, "display") or _contains_keyword(text, "device"):
        startup_score += 1

    if image_score > 0 and platform_score >= 2:
        image_score -= 1

    if ai_signal_score == 0:
        return "hot_news"

    scores = {
        "image_video": image_score,
        "llm": llm_score,
        "startup": startup_score,
        "hot_news": hot_news_score,
    }
    best_category = max(scores, key=scores.get)
    if scores[best_category] <= 0:
        return "hot_news"
    return best_category


def _fallback_classify_items(items: List[PipelineItem]) -> List[PipelineItem]:
    out: List[PipelineItem] = []
    for item in items:
        cloned = PipelineItem.from_dict(item.to_dict())
        if cloned.source == "Product Hunt" or "producthunt.com/products" in cloned.url:
            cloned.category = "startup"
        else:
            cloned.category = _classify_item(cloned)
        out.append(cloned)
    return out


def _fallback_dedup_items(items: List[PipelineItem]) -> List[PipelineItem]:
    deduped: List[PipelineItem] = []
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()

    for item in items:
        normalized_url = item.url.strip()
        normalized_title = item.title.strip().lower()
        if normalized_url and normalized_url in seen_urls:
            continue
        if normalized_title and normalized_title in seen_titles:
            continue
        if normalized_url:
            seen_urls.add(normalized_url)
        if normalized_title:
            seen_titles.add(normalized_title)
        deduped.append(PipelineItem.from_dict(item.to_dict()))

    return deduped


def normalize_node(state: PipelineState, prompt_loader: Any, invoker: Callable[[str], str]) -> Dict[str, Any]:
    """标准化：input_items -> normalized_items。"""
    input_list = state.get("input_items") or []
    if not input_list:
        return {"normalized_items": [], "error": None}
    text = _run_prompt(prompt_loader, invoker, "normalize", json.dumps(input_list, ensure_ascii=False))
    data = parse_json_from_model_output(text)
    items = json_list_to_items(data) if data else []
    if not items:
        raise RuntimeError("normalize returned no items; refusing to use fallback output")
    raw_by_url = {
        str(raw.get("url") or "").strip(): raw
        for raw in input_list
        if str(raw.get("url") or "").strip()
    }
    for it in items:
        it.category = None
        raw = raw_by_url.get(it.url)
        if raw and raw.get("product_rank") is not None and it.product_rank is None:
            try:
                it.product_rank = int(raw.get("product_rank"))
            except (TypeError, ValueError):
                pass
        if raw and raw.get("logo_url") and not it.logo_url:
            it.logo_url = str(raw.get("logo_url")).strip() or None
    return {"normalized_items": items, "error": None}


def classify_node(state: PipelineState, prompt_loader: Any, invoker: Callable[[str], str]) -> Dict[str, Any]:
    """分类：normalized_items -> categorized_items。"""
    items = state.get("normalized_items") or []
    if not items:
        return {"categorized_items": [], "error": None}
    text = _run_prompt(prompt_loader, invoker, "classify", json.dumps(items_to_json_list(items), ensure_ascii=False))
    data = parse_json_from_model_output(text)
    categorized_items = json_list_to_items(data) if data else []
    if not categorized_items:
        raise RuntimeError("classify returned no items; refusing to use fallback output")
    original_by_url = {it.url: it for it in items if it.url}
    for it in categorized_items:
        original = original_by_url.get(it.url)
        if original and original.logo_url and not it.logo_url:
            it.logo_url = original.logo_url
    return {"categorized_items": categorized_items, "error": None}


def dedup_node(state: PipelineState, prompt_loader: Any, invoker: Callable[[str], str]) -> Dict[str, Any]:
    """去重：categorized_items -> deduped_items。"""
    items = state.get("categorized_items") or []
    if not items:
        return {"deduped_items": [], "error": None}
    text = _run_prompt(prompt_loader, invoker, "dedup", json.dumps(items_to_json_list(items), ensure_ascii=False))
    data = parse_json_from_model_output(text)
    deduped_items = json_list_to_items(data) if data else []
    if not deduped_items:
        raise RuntimeError("dedup returned no items; refusing to use fallback output")
    original_by_url = {it.url: it for it in items if it.url}
    for it in deduped_items:
        original = original_by_url.get(it.url)
        if original and original.logo_url and not it.logo_url:
            it.logo_url = original.logo_url
    return {"deduped_items": deduped_items, "error": None}


def reflect_node(state: PipelineState, prompt_loader: Any, invoker: Callable[[str], str]) -> Dict[str, Any]:
    """反思：输出 need_rerun 与 issues，若 need_rerun 则递增 iteration。"""
    items = state.get("deduped_items") or []
    if not items:
        return {"reflection_notes": {"need_rerun": False, "issues": []}, "error": None}
    text = _run_prompt(prompt_loader, invoker, "reflect", json.dumps(items_to_json_list(items), ensure_ascii=False))
    notes = parse_json_from_model_output(text)
    if not isinstance(notes, dict):
        raise RuntimeError("reflect returned invalid JSON object")
    out = {"reflection_notes": notes, "error": None}
    if notes.get("need_rerun"):
        out["iteration"] = state.get("iteration", 0) + 1
    return out


def _route_after_reflect(state: PipelineState) -> str:
    notes = state.get("reflection_notes") or {}
    if not isinstance(notes, dict):
        return "end"
    if notes.get("need_rerun", False) and state.get("iteration", 0) <= MAX_REFLECTION_ITERATIONS:
        return "retry"
    return "end"


class ProcessingPipeline:
    """处理流水线：持有 PromptLoader 与 invoker，构建 LangGraph 图并执行。"""

    def __init__(self, prompt_loader: PromptLoader | None = None, invoker: Any = None):
        self.prompt_loader = prompt_loader or PromptLoader()
        self.invoker = invoker or get_llm_invoker()
        self._graph = None

    def _bind_normalize(self, state: PipelineState) -> Dict[str, Any]:
        return normalize_node(state, self.prompt_loader, self.invoker)

    def _bind_classify(self, state: PipelineState) -> Dict[str, Any]:
        return classify_node(state, self.prompt_loader, self.invoker)

    def _bind_dedup(self, state: PipelineState) -> Dict[str, Any]:
        return dedup_node(state, self.prompt_loader, self.invoker)

    def _bind_reflect(self, state: PipelineState) -> Dict[str, Any]:
        return reflect_node(state, self.prompt_loader, self.invoker)

    def build_graph(self) -> StateGraph:
        builder = StateGraph(PipelineState)
        builder.add_node("normalize", self._bind_normalize)
        builder.add_node("classify", self._bind_classify)
        builder.add_node("dedup", self._bind_dedup)
        builder.add_node("reflect", self._bind_reflect)
        builder.add_edge(START, "normalize")
        builder.add_edge("normalize", "classify")
        builder.add_edge("classify", "dedup")
        builder.add_edge("dedup", "reflect")
        builder.add_conditional_edges("reflect", _route_after_reflect, {"retry": "classify", "end": END})
        self._graph = builder.compile()
        return self._graph

    @property
    def graph(self):
        if self._graph is None:
            self.build_graph()
        return self._graph

    def run(self, input_items: List[Dict[str, Any]], initial_state: Dict[str, Any] | None = None) -> Dict[str, Any]:
        state: Dict[str, Any] = dict(initial_state or {})
        state["input_items"] = input_items
        state["iteration"] = 0
        return self.graph.invoke(state)
