# consistency_checker.py
# -*- coding: utf-8 -*-
from typing import Optional

from ..adapters.llm_adapters import create_llm_adapter

# ============== 增加对"剧情要点/未解决冲突"和"角色动机合理性"进行检查的可选引导 ==============
CONSISTENCY_PROMPT = """\
请检查下面的小说设定与最新章节是否存在明显冲突或不一致之处，如有请列出：
- 小说设定：
{novel_setting}

- 角色状态（可能包含重要信息）：
{character_state}

- 前文摘要：
{global_summary}

- 已记录的未解决冲突或剧情要点：
{plot_arcs}  # 若为空可能不输出

- 最新章节内容：
{chapter_text}

⚠️ 检查项（请逐项检查）：

1. **设定一致性**：
   - 世界观规则是否前后一致（如魔法体系、科技设定、社会规则等）
   - 角色能力/物品属性是否与设定矛盾
   - 时间线、地理位置是否合理

2. **角色行为动机合理性（重点检查）**：
   - 从"角色状态→行为动机"模块提取角色的"核心驱动力"和"当前目标"
   - 检查本章角色的重要决策是否符合其动机：
     * 角色行为是否与"核心驱动力"一致？
     * 若出现动机转变，是否有合理的触发事件？
     * 是否存在"为剧情需要而行动"的不合理行为？
   - 示例问题：
     * "角色A的动机是保护家人，但本章在家人危险时选择逃跑，且无内心挣扎描写"
     * "角色B上一章还坚定追求权力，本章无缘由地突然放弃，缺乏动机演变过程"

3. **剧情推进合理性**：
   - 是否推进了未解决的重要伏笔（从"已记录的未解决冲突或剧情要点"中查看）
   - 是否存在被忽略或应该推进但未推进的重要线索
   - 新增伏笔是否与已有设定冲突

4. **角色状态更新一致性**：
   - 本章角色的物品、能力、位置等是否与前文一致
   - 角色关系变化是否有合理铺垫

如果存在冲突或不一致，请按以下格式列出：
【问题类型】问题描述 + 具体位置（如"第X段"或引用原文片段）

如果未解决冲突中有被忽略或需要推进的地方，也请提及。

如果以上检查项均无明显问题，请返回"无明显冲突"。
"""

def check_consistency(
    novel_setting: str,
    character_state: str,
    global_summary: str,
    chapter_text: str,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float = 0.3,
    plot_arcs: str = "",
    interface_format: str = "OpenAI",
    max_tokens: int = 2048,
    timeout: int = 600,
    system_prompt: Optional[str] = None
) -> str:
    """
    调用模型做简单的一致性检查。可扩展更多提示或校验规则。
    新增: 会额外检查对“未解决冲突或剧情要点”（plot_arcs）的衔接情况。
    """
    prompt = CONSISTENCY_PROMPT.format(
        novel_setting=novel_setting,
        character_state=character_state,
        global_summary=global_summary,
        plot_arcs=plot_arcs,
        chapter_text=chapter_text
    )

    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )

    active_system_prompt = (system_prompt or "").strip()

    # 调试日志
    if active_system_prompt:
        print("[ConsistencyChecker] System Prompt >>>", active_system_prompt)
    print("[ConsistencyChecker] Prompt >>>", prompt)

    response = llm_adapter.invoke(prompt, system_prompt=active_system_prompt)
    if not response:
        return "审校Agent无回复"

    # 调试日志
    print("[ConsistencyChecker] Response <<<", response)

    return response

