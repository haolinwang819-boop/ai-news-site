"""
AI 资讯处理流水线脚本包。
"""
from .pipeline import ProcessingPipeline
from .run import main as run_main

__all__ = ["ProcessingPipeline", "run_main"]
