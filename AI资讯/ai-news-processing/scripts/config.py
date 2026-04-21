"""
处理流水线配置：路径、LLM、反思最大轮数等。
"""
import os
from pathlib import Path


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


def _default_provider() -> str:
    explicit = os.environ.get("LLM_PROVIDER")
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

# LLM 配置（可从环境变量覆盖）
LLM_CONFIG = {
    "provider": _default_provider(),  # openai | anthropic | gemini
    "model": os.environ.get("LLM_MODEL", ""),
    "api_key": (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or os.environ.get("ANTHROPIC_API_KEY", "")
    ),
    "temperature": 0.1,
}

