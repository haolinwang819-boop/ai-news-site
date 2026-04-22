"""
处理流水线配置：路径、两阶段 LLM、筛选并发参数等。
"""
import os
from pathlib import Path
from typing import Any


def _load_root_env_file():
    """向上查找工作区根目录的 .env.local，并填充到 os.environ。"""
    for base in Path(__file__).resolve().parents:
        env_path = base / ".env.local"
        if not env_path.exists():
            continue

        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]

            os.environ.setdefault(key, value)
        return


def _default_provider(explicit_env: str | None = "LLM_PROVIDER") -> str:
    explicit = os.environ.get(explicit_env or "") if explicit_env else None
    if explicit:
        return explicit
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return "openai"


_load_root_env_file()

# 本包根目录（ai-news-processing）
ROOT_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = ROOT_DIR / "prompts"
DATA_DIR = ROOT_DIR / "data"
DIGESTS_DIR = DATA_DIR / "digests"

# 反思最多回流轮数（避免死循环）
MAX_REFLECTION_ITERATIONS = 2

DEFAULT_MODELS = {
    "openai": {
        "selection": "gpt-4o-mini",
        "editor": "gpt-5.4",
    },
    "anthropic": {
        "selection": "claude-3-5-haiku-latest",
        "editor": "claude-3-7-sonnet-latest",
    },
    "gemini": {
        "selection": "gemini-3-flash-preview",
        "editor": "gemini-3.1-pro-preview",
    },
}


def _first_env(names: tuple[str, ...], default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value not in (None, ""):
            return value
    return default


def _api_key_for_provider(provider: str) -> str:
    provider = (provider or "").lower()
    if provider == "gemini":
        return os.environ.get("GEMINI_API_KEY", "")
    if provider == "openai":
        return os.environ.get("OPENAI_API_KEY", "")
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_API_KEY", "")
    return ""


def _default_model(provider: str, role: str) -> str:
    return DEFAULT_MODELS.get(provider, DEFAULT_MODELS["openai"]).get(role, "")


def _int_env(names: tuple[str, ...], default: int) -> int:
    value = _first_env(names, "")
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _build_llm_config(role: str) -> dict[str, Any]:
    is_editor = role == "editor"
    provider = _first_env(
        (
            f"LLM_{role.upper()}_PROVIDER",
            "LLM_PROVIDER" if is_editor else "",
        ),
        _default_provider(None),
    ).lower()
    model = _first_env(
        (
            f"LLM_{role.upper()}_MODEL",
            "LLM_MODEL" if is_editor else "",
        ),
        _default_model(provider, role),
    )
    return {
        "provider": provider,
        "model": model,
        "api_key": _api_key_for_provider(provider),
        "temperature": float(_first_env((f"LLM_{role.upper()}_TEMPERATURE",), "0.1") or "0.1"),
        "max_tokens": _int_env(
            (f"LLM_{role.upper()}_MAX_TOKENS", "LLM_MAX_TOKENS" if is_editor else ""),
            32768 if is_editor else 8192,
        ),
        "timeout_seconds": _int_env(
            (f"LLM_{role.upper()}_TIMEOUT_SECONDS", "LLM_TIMEOUT_SECONDS" if is_editor else ""),
            240 if is_editor else 180,
        ),
        "thinking_level": _first_env(
            (f"LLM_{role.upper()}_THINKING_LEVEL", "LLM_THINKING_LEVEL" if is_editor else ""),
            "low",
        ),
        "response_mime_type": _first_env(
            (
                f"LLM_{role.upper()}_RESPONSE_MIME_TYPE",
                "LLM_RESPONSE_MIME_TYPE" if is_editor else "",
            ),
            "application/json",
        ),
        "request_attempts": _int_env(
            (f"LLM_{role.upper()}_REQUEST_ATTEMPTS", "LLM_REQUEST_ATTEMPTS" if is_editor else ""),
            3 if is_editor else 2,
        ),
    }


LLM_SELECTION_CONFIG = _build_llm_config("selection")
LLM_EDITOR_CONFIG = _build_llm_config("editor")

# 保留旧常量名，避免现有导入立即崩掉；新代码应优先用 LLM_EDITOR_CONFIG。
LLM_CONFIG = LLM_EDITOR_CONFIG

SCREENING_CONFIG = {
    "max_workers": _int_env(("LLM_SELECTION_MAX_WORKERS",), 10),
    "chunk_size": _int_env(("LLM_SELECTION_CHUNK_SIZE",), 18),
    "max_items": _int_env(("LLM_SELECTION_MAX_ITEMS",), 30),
    "chunk_retry_attempts": _int_env(("LLM_SELECTION_CHUNK_RETRY_ATTEMPTS",), 3),
    "failure_ratio_threshold": float(_first_env(("LLM_SELECTION_FAILURE_RATIO_THRESHOLD",), "0.2") or "0.2"),
    "per_source_cap": _int_env(("LLM_SELECTION_PER_SOURCE_CAP",), 12),
    "min_content_length": _int_env(("LLM_SELECTION_MIN_CONTENT_LENGTH",), 40),
    "shortlist_targets": {
        "breakout_products": _int_env(("LLM_SELECTION_BREAKOUT_TARGET",), 8),
        "hot_news": _int_env(("LLM_SELECTION_HOT_NEWS_TARGET",), 8),
        "llm": _int_env(("LLM_SELECTION_LLM_TARGET",), 6),
        "image_video": _int_env(("LLM_SELECTION_IMAGE_VIDEO_TARGET",), 4),
        "product_updates": _int_env(("LLM_SELECTION_PRODUCT_UPDATES_TARGET",), 4),
    },
}

