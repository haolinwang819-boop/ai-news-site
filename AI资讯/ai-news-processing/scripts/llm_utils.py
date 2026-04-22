"""
Prompt 加载、LLM 调用、模型输出解析。
"""
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, List, Mapping, Optional

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


def get_llm_invoker(
    config: Mapping[str, Any] | None = None,
    *,
    label: str = "llm",
) -> Callable[[str], str]:
    """根据给定配置返回 invoke(prompt: str) -> str。"""
    active_config = dict(LLM_CONFIG)
    if config:
        active_config.update(dict(config))

    provider = (active_config.get("provider") or "openai").lower()
    default_models = {
        "openai": "gpt-5.4",
        "anthropic": "claude-3-5-haiku-latest",
        "gemini": "gemini-3.1-pro-preview",
    }
    model = active_config.get("model") or default_models.get(provider, "gpt-5.4")
    api_key = active_config.get("api_key") or ""
    temperature = active_config.get("temperature", 0.1)
    max_tokens = active_config.get("max_tokens", 8192)
    timeout_seconds = int(active_config.get("timeout_seconds", 240))
    thinking_level = str(active_config.get("thinking_level") or "").strip()
    response_mime_type = str(active_config.get("response_mime_type") or "").strip()
    request_attempts = max(int(active_config.get("request_attempts", 1)), 1)

    if not api_key:
        raise ValueError("请设置环境变量 GEMINI_API_KEY、OPENAI_API_KEY 或 ANTHROPIC_API_KEY")

    print(f"LLM[{label}] provider={provider}, model={model}", file=sys.stderr)

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=model, temperature=temperature, max_tokens=max_tokens, api_key=api_key)
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        llm = ChatAnthropic(model=model, temperature=temperature, max_tokens=max_tokens, api_key=api_key)
    elif provider == "gemini":
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

        def invoke(prompt: str) -> str:
            active_prompt = prompt
            last_data: dict[str, Any] | None = None

            for attempt in range(1, request_attempts + 1):
                generation_config = {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                }
                if response_mime_type:
                    generation_config["responseMimeType"] = response_mime_type
                if thinking_level:
                    generation_config["thinkingConfig"] = {"thinkingLevel": thinking_level}

                payload = {
                    "contents": [{"parts": [{"text": active_prompt}]}],
                    "generationConfig": generation_config,
                }
                response = requests.post(
                    endpoint,
                    params={"key": api_key},
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=timeout_seconds,
                )
                response.raise_for_status()
                data = response.json()
                last_data = data

                candidates = data.get("candidates") or []
                if not candidates:
                    raise ValueError(f"Gemini 返回为空: {data}")

                parts = candidates[0].get("content", {}).get("parts", [])
                text_parts = [part.get("text", "") for part in parts if part.get("text")]
                if text_parts:
                    return "".join(text_parts)

                finish_reason = candidates[0].get("finishReason")
                if finish_reason == "MAX_TOKENS" and attempt < request_attempts:
                    active_prompt = (
                        prompt
                        + "\n\nThe previous response ended with MAX_TOKENS before producing text. "
                        + "Retry with compact JSON only. Use the shortest valid output that satisfies the schema. "
                        + "Do not include reasoning, commentary, or any text outside JSON."
                    )
                    continue

                raise ValueError(f"Gemini 未返回文本内容: {data}")

            raise ValueError(f"Gemini 未返回文本内容: {last_data}")

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
