#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
DOC_PATH="$ROOT_DIR/Nexttoken.docx"

if [[ ! -f "$DOC_PATH" ]]; then
  echo "Nexttoken.docx not found: $DOC_PATH" >&2
  exit 1
fi

if ! command -v textutil >/dev/null 2>&1; then
  echo "textutil is required to read Nexttoken.docx" >&2
  exit 1
fi

SECTION="${1:-summary}"

print_usage() {
  cat <<'EOF'
Usage:
  extract_nexttoken_sources.sh summary
  extract_nexttoken_sources.sh x
  extract_nexttoken_sources.sh instagram
  extract_nexttoken_sources.sh xhs
  extract_nexttoken_sources.sh wechat
  extract_nexttoken_sources.sh tools
  extract_nexttoken_sources.sh news
  extract_nexttoken_sources.sh reddit
  extract_nexttoken_sources.sh all
EOF
}

extract_all() {
  textutil -convert txt -stdout "$DOC_PATH"
}

extract_range() {
  local start="$1"
  local end="$2"
  extract_all | sed -n "${start},${end}p"
}

case "$SECTION" in
  summary)
    cat <<'EOF'
Nexttoken section summary
- x: lines 1-435
- instagram: lines 436-519
- xhs: lines 520-688
- wechat: lines 689-803
- tools: lines 804-1758
- news: lines 1759-2089
- reddit: lines 2090-2127
EOF
    ;;
  x)
    extract_range 1 435
    ;;
  instagram|ins)
    extract_range 436 519
    ;;
  xhs|xiaohongshu)
    extract_range 520 688
    ;;
  wechat|gzh|gongzhonghao)
    extract_range 689 803
    ;;
  tools|sites|products)
    extract_range 804 1758
    ;;
  news|research)
    extract_range 1759 2089
    ;;
  reddit)
    extract_range 2090 2127
    ;;
  all)
    extract_all
    ;;
  *)
    print_usage >&2
    exit 1
    ;;
esac
