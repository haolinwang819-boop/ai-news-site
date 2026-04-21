# AI 资讯处理流水线（LangGraph）

本目录为资讯处理流水线：**标准化 → 分类 → 去重 → 反思（可选回流）**，prompt 在 `prompts/` 下可单独修改。

## 环境

```bash
cd ai-news-processing
pip install -r requirements.txt
```

设置 LLM：

- OpenAI：`export OPENAI_API_KEY=sk-...`
- Anthropic：`export ANTHROPIC_API_KEY=...` 且 `export LLM_PROVIDER=anthropic`。

## 运行

从 **ai-news-processing** 目录执行：

```bash
# 从文件读抓取条目（JSON 数组或 JSONL）
python run.py path/to/items.json

# 从 stdin
cat items.json | python run.py -
python run.py - < items.json
```

输出写入 `data/digests/YYYY-MM-DD.json`，结构见《处理流程与数据规范》2.2。

## 目录与 prompt

- **prompts/**：
  - `normalize.md`：标准化
  - `classify.md`：分类（四板块）
  - `dedup.md`：去重
  - `reflect.md`：反思（是否回流）
- **scripts/**：`config.py` 配置；`models.py` 数据与状态；`llm_utils.py` Prompt/LLM/解析；`pipeline.py` 图与节点；`run.py` 入口。
- **data/digests/**：日报 JSON 输出。

## 输入格式

抓取条目建议包含：`title`, `url`, `source`, `published_time`, `content`，可选 `image_url`；`priority` 由标准化节点大模型判断。与《处理流程与数据规范》第一节一致。
