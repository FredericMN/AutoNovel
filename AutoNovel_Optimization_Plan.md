# AutoNovel 深度优化方案规划

## 1. 方案 A：伏笔"直通车"机制 (Plot Arcs "Direct Access")

**目标**：解决长篇连贯性问题，确保 LLM 在生成新章节时能直接感知到未解决的详细伏笔，而不仅仅是依赖高度概括的摘要。

**实施细节**：
1.  **修改 `novel_generator/chapter.py`**：
    -   在 `build_chapter_prompt` 函数中增加读取 `plot_arcs.txt` 的逻辑。
    -   解析文件，提取 **[A级-主线]** 和 **[B级-支线]** 的未解决伏笔。
    -   格式化这些伏笔为独立的上下文块。
2.  **修改 `core/prompting/prompt_definitions.py`**：
    -   更新 `next_chapter_draft_prompt` 和 `first_chapter_draft_prompt`，增加 `{unresolved_plot_arcs}` 占位符。
    -   在提示词中明确指示 LLM 参考这些伏笔进行铺垫或回收。

**预期收益**：大幅提升剧情连贯性和伏笔回收的精准度。

---

## 2. 方案 B：流水线式摘要缓存 (Pipelined Summary Caching)

**目标**：降低 Token 消耗，提升生成速度，减少重复计算。

**实施细节**：
1.  **修改 `novel_generator/finalization.py`**：
    -   在 `finalize_chapter` 完成后，立即调用 LLM 生成当章的独立摘要（约300-500字）。
    -   保存为 `chapters/chapter_X_summary.txt`。
2.  **修改 `core/prompting/prompt_definitions.py`**：
    -   新增 `single_chapter_summary_prompt` 用于生成单章摘要。
3.  **修改 `novel_generator/chapter.py`**：
    -   重构上下文获取逻辑。在读取"最近3章"时，优先读取 `chapter_summary.txt`。
    -   采用混合模式：`Summary(N-3) + Summary(N-2) + RawText(N-1)`。
    -   更新 `summarize_recent_chapters` 逻辑，利用缓存摘要快速生成过渡摘要，或直接拼接。

**预期收益**：Token 消耗降低约 60%，生成速度提升。

---

## 3. 方案 C："批评家-作家"双循环模式 (Critic-Refine Loop)

**目标**：提升文学性，减少 AI 生成感，自我修正逻辑漏洞。

**实施细节**：
1.  **修改 `core/prompting/prompt_definitions.py`**：
    -   新增 `chapter_critique_prompt`（批评家）：用于指出草稿问题。
    -   新增 `chapter_refine_prompt`（作家）：用于根据意见重写。
2.  **修改 `novel_generator/chapter.py`**：
    -   在 `generate_chapter_draft` 中增加 Refine 流程。
    -   生成初稿 -> 调用 Critic 提出意见 -> 调用 Refiner 重写。
    -   增加配置开关（如在 `config.json` 或参数中控制），默认启用或可选。

**预期收益**：显著提升单章的文学质量和逻辑严密性。
