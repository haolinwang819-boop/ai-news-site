"""
Prompt 加载、LLM 调用、模型输出解析。
"""
import json
import re
from pathlib import Path
from typing import Any, Callable, List, Optional

import requests

from .config import LLM_CONFIG, PROMPTS_DIR


class PromptLoader:
    """按名称加载 prompts/*.md 并替换 {{variable}} 占位符。"""

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or PROMPTS_DIR

    def load(self, name: str, **variables: str) -> str:
        path = self.base_dir / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        text = path.read_text(encoding="utf-8")
        for key, value in variables.items():
            text = text.replace("{{" + key + "}}", value)
        return text

    def load_plain(self, name: str) -> str:
        """仅加载文件内容，不替换变量。"""
        path = self.base_dir / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8")


def get_llm_invoker() -> Callable[[str], str]:
    """根据 LLM_CONFIG 返回 invoke(prompt: str) -> str。"""
    provider = (LLM_CONFIG.get("provider") or "openai").lower()
    default_models = {
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-latest",
        "gemini": "gemini-2.5-flash",
    }
    model = LLM_CONFIG.get("model") or default_models.get(provider, "gpt-4o-mini")
    api_key = LLM_CONFIG.get("api_key") or ""
    temperature = LLM_CONFIG.get("temperature", 0.1)
    max_tokens = LLM_CONFIG.get("max_tokens", 8192)

    if not api_key:
        raise ValueError("请设置环境变量 OPENAI_API_KEY 或 ANTHROPIC_API_KEY")

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=model, temperature=temperature, max_tokens=max_tokens, api_key=api_key)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model=model, temperature=temperature, max_tokens=max_tokens, api_key=api_key)
    elif provider == "gemini":
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        def invoke(prompt: str) -> str:
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            }
            response = requests.post(
                endpoint,
                params={"key": api_key},
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            candidates = data.get("candidates") or []
            if not candidates:
                raise ValueError(f"Gemini 返回为空: {data}")

            parts = candidates[0].get("content", {}).get("parts", [])
            text_parts = [part.get("text", "") for part in parts if part.get("text")]
            if not text_parts:
                raise ValueError(f"Gemini 未返回文本内容: {data}")
            return "".join(text_parts)

        return invoke
    else:
        raise ValueError(f"不支持的 LLM provider: {provider}")

    def invoke(prompt: str) -> str:
        msg = llm.invoke(prompt)
        return msg.content if hasattr(msg, "content") else str(msg)
    return invoke


def parse_json_from_model_output(text: str) -> Any:
    """从模型输出中解析 JSON，兼容 ```json ... ``` 包裹。"""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    return json.loads(text)


def chunk_list(lst: List[Any], size: int):
    """将列表按 size 分批迭代。"""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]
