#!/usr/bin/env python3
"""
从项目根（ai-news-processing）运行流水线：
  python run.py [input_file]
  python run.py -  < items.json
  echo '[{"title":"..."}]' | python run.py -
"""
import sys
from pathlib import Path

# 保证以项目根为 path，便于 scripts 作为包加载
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from scripts.run import main

if __name__ == "__main__":
    main()
