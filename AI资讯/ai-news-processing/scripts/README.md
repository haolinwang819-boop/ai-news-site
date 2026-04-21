# scripts 脚本说明

本目录为 AI 资讯处理流水线的实现，各脚本作用如下。

---

## config.py

**作用**：集中存放流水线所需的配置。

- **路径**：`ROOT_DIR`（项目根）、`PROMPTS_DIR`（prompts/）、`DATA_DIR`（data/）、`DIGESTS_DIR`（data/digests/），其它脚本从这里读取路径。
- **反思轮数**：`MAX_REFLECTION_ITERATIONS`，反思节点最多让流程回到「分类」的次数，避免死循环。
- **LLM 配置**：`LLM_CONFIG` 中的 provider（openai / anthropic）、model、api_key、temperature 等，可由环境变量覆盖（如 `OPENAI_API_KEY`、`ANTHROPIC_API_KEY`、`LLM_PROVIDER`、`LLM_MODEL`）。

---

## models.py

**作用**：定义流水线中使用的数据结构和图状态。

- **PipelineItem**：单条资讯的 dataclass，与《处理流程与数据规范》中的单条条目格式一致。字段包括 title、url、source、published_time、priority、content、image_url、category（分类后才有）。提供 `to_dict()`、`from_dict()` 便于与 JSON/字典互转。
- **items_to_json_list**：将 `List[PipelineItem]` 转为可序列化的 `List[dict]`。
- **json_list_to_items**：将 `List[dict]` 转为 `List[PipelineItem]`。
- **PipelineState**：LangGraph 图状态的 TypedDict，包含 input_items、normalized_items、categorized_items、deduped_items、reflection_notes、iteration、error 等键，各节点通过读写这些键传递数据。

---

## llm_utils.py

**作用**：Prompt 加载、LLM 调用、模型输出解析等与「和模型交互」相关的工具。

- **PromptLoader**：从 `prompts/` 目录按名称加载 `.md` 文件（如 `load("normalize")` 对应 `prompts/normalize.md`），并替换模板中的 `{{变量名}}`（如 `{{input_json}}`），实现框架与 prompt 分离。
- **get_llm_invoker()**：根据 `config.LLM_CONFIG` 创建 OpenAI 或 Anthropic 的调用封装，返回一个函数 `invoke(prompt: str) -> str`，供节点调用。
- **parse_json_from_model_output(text)**：从模型返回的字符串中解析 JSON，兼容直接输出 JSON 或被 \`\`\`json ... \`\`\` 包裹的情况。
- **chunk_list**：将列表按指定大小分批迭代，预留作大批量条目分批调用 LLM 时使用。

---

## pipeline.py

**作用**：实现 LangGraph 的四个节点与图构建，并封装为可执行的流水线类。

- **四个节点函数**：
  - **normalize_node**：从 state 的 `input_items` 读取抓取条目，调用 `prompts/normalize.md` 做标准化（统一字段、赋 priority 等），写回 `normalized_items`。
  - **classify_node**：从 `normalized_items` 读取，调用 `prompts/classify.md` 为每条打上 category（四板块之一），写回 `categorized_items`。
  - **dedup_node**：从 `categorized_items` 读取，调用 `prompts/dedup.md` 做同事件/同 URL 去重，写回 `deduped_items`。
  - **reflect_node**：从 `deduped_items` 读取，调用 `prompts/reflect.md` 做质量检查，输出 `need_rerun` 与 `issues`，写回 `reflection_notes`；若 need_rerun 则递增 `iteration`。
- **_route_after_reflect**：反思后的条件路由：若 need_rerun 且未超过最大轮数则回到「分类」，否则结束。
- **ProcessingPipeline**：持有 PromptLoader 与 invoker，`build_graph()` 将上述节点连成图（normalize → classify → dedup → reflect → 条件边），`run(input_items)` 执行流水线并返回最终 state（结果在 `deduped_items`）。

---

## run.py

**作用**：命令行入口，负责读输入、跑流水线、写日报文件。

- **_ensure_digests_dir()**：确保 `data/digests/` 目录存在。
- **_build_digest(deduped_items, date)**：将去重后的条目按 category 分成四类，组装成规范中的日报 JSON 结构（date、generated_at、total_count、categories）。
- **main()**：解析命令行参数（输入文件或 `-` 表示 stdin，可选 `-o` 输出路径、`--date` 日报日期）；读取 JSON 数组或 JSONL；调用 `ProcessingPipeline().run(items)`；从返回的 state 取 `deduped_items`，生成日报并写入 `data/digests/YYYY-MM-DD.json`（或 `-o` 指定路径）。

在项目根执行 `python run.py` 或 `python -m scripts.run` 时，实际运行的是此脚本的 `main()`。

---

## __init__.py

**作用**：将本目录声明为 Python 包，并对包外暴露主要接口。

- 导出 `ProcessingPipeline`（来自 pipeline）和 `run_main`（即 run.main），便于其它代码通过 `from scripts import ProcessingPipeline, run_main` 使用。
