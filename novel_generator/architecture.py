#novel_generator/architecture.py
# -*- coding: utf-8 -*-
"""
小说总体架构生成（Novel_architecture_generate 及相关辅助函数）
"""
import os
import json
import logging
import traceback
from novel_generator.common import invoke_with_cleaning
from llm_adapters import create_llm_adapter
from prompt_definitions import (
    core_seed_prompt,
    character_dynamics_prompt,
    world_building_prompt,
    plot_architecture_prompt,
    volume_breakdown_prompt,  # 新增：分卷架构提示词
    create_character_state_prompt,
    resolve_global_system_prompt
)
logging.basicConfig(
    filename='app.log',      # 日志文件名
    filemode='a',            # 追加模式（'w' 会覆盖）
    level=logging.INFO,      # 记录 INFO 及以上级别的日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
from utils import clear_file_content, save_string_to_txt
from volume_utils import calculate_volume_ranges  # 新增：分卷工具函数


def generate_volume_architecture(
    llm_adapter,
    novel_architecture: str,
    num_volumes: int,
    num_chapters: int,
    volume_ranges: list,
    system_prompt: str = "",
    gui_log_callback=None
) -> str:
    """
    生成分卷架构规划

    Args:
        llm_adapter: LLM适配器
        novel_architecture: 总体架构文本
        num_volumes: 分卷数量
        num_chapters: 总章节数
        volume_ranges: 卷范围列表 [(start, end), ...]
        system_prompt: 系统提示词
        gui_log_callback: GUI日志回调函数

    Returns:
        分卷架构文本
    """
    def gui_log(msg):
        if gui_log_callback:
            gui_log_callback(msg)
        logging.info(msg)

    # 构建动态格式示例
    volume_format_examples = []
    for i, (vol_start, vol_end) in enumerate(volume_ranges, 1):
        if i == 1:
            # 第一卷格式
            example = f"""第一卷（第{vol_start}-{vol_end}章）
卷标题：[为本卷起一个副标题]
核心冲突：[本卷的主要矛盾]
├── 第一幕（触发）：[起因事件与初始冲突]
├── 第二幕（对抗）：[矛盾升级与角色成长]
├── 第三幕（解决）：[阶段性结局，可留悬念]
└── 卷末伏笔：[为下一卷铺垫的3个关键要素]"""
        elif i == num_volumes:
            # 最后一卷格式
            example = f"""第{i}卷（第{vol_start}-{vol_end}章）
卷标题：[副标题]
核心冲突：[终极矛盾]
├── 承接点：[如何继承第{i-1}卷]
├── 第一幕（触发）：[终极冲突的触发]
├── 第二幕（对抗）：[最高潮的较量]
├── 第三幕（解决）：[完整收束所有主线和关键支线]
└── 全书总结：[整体主题的升华]"""
        else:
            # 中间卷格式
            example = f"""第{i}卷（第{vol_start}-{vol_end}章）
卷标题：[副标题]
核心冲突：[升级的矛盾]
├── 承接点：[如何继承第{i-1}卷]
├── 第一幕（触发）：[新的触发事件]
├── 第二幕（对抗）：[更深层的冲突]
├── 第三幕（解决）：[阶段性结局]
└── 卷末伏笔：[为下一卷铺垫的要素]"""

        volume_format_examples.append(example)

    volume_format_str = "\n\n".join(volume_format_examples)

    # 构建 prompt 参数
    format_params = {
        "novel_architecture": novel_architecture,
        "num_volumes": num_volumes,
        "num_chapters": num_chapters,
        "volume_format_examples": volume_format_str
    }

    gui_log("   ├─ 向LLM发起请求...")
    prompt = volume_breakdown_prompt.format(**format_params)
    result = invoke_with_cleaning(llm_adapter, prompt, system_prompt=system_prompt)

    if not result or not result.strip():
        gui_log("   └─ ⚠ 生成结果为空")
        logging.warning("Volume architecture generation returned empty result")
        return ""

    return result


def load_partial_architecture_data(filepath: str) -> dict:
    """
    从 filepath 下的 partial_architecture.json 读取已有的阶段性数据。
    如果文件不存在或无法解析，返回空 dict。
    """
    partial_file = os.path.join(filepath, "partial_architecture.json")
    if not os.path.exists(partial_file):
        return {}
    try:
        with open(partial_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        logging.warning(f"Failed to load partial_architecture.json: {e}")
        return {}

def save_partial_architecture_data(filepath: str, data: dict):
    """
    将阶段性数据写入 partial_architecture.json。
    """
    partial_file = os.path.join(filepath, "partial_architecture.json")
    try:
        with open(partial_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"Failed to save partial_architecture.json: {e}")

def Novel_architecture_generate(
    interface_format: str,
    api_key: str,
    base_url: str,
    llm_model: str,
    topic: str,
    genre: str,
    number_of_chapters: int,
    word_number: int,
    filepath: str,
    num_volumes: int = 0,  # 新增：分卷数量（0或1表示不分卷）
    user_guidance: str = "",  # 新增参数
    use_global_system_prompt: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    timeout: int = 600,
    gui_log_callback=None  # 新增GUI日志回调
) -> None:
    """
    依次调用:
      1. core_seed_prompt
      2. character_dynamics_prompt
      3. world_building_prompt
      4. plot_architecture_prompt
    若在中间任何一步报错且重试多次失败，则将已经生成的内容写入 partial_architecture.json 并退出；
    下次调用时可从该步骤继续。
    最终输出 Novel_architecture.txt

    新增：
    - 在完成角色动力学设定后，依据该角色体系，使用 create_character_state_prompt 生成初始角色状态表，
      并存储到 character_state.txt，后续维护更新。
    """
    os.makedirs(filepath, exist_ok=True)
    partial_data = load_partial_architecture_data(filepath)
    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=llm_model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )
    system_prompt = resolve_global_system_prompt(use_global_system_prompt)

    # GUI日志辅助函数
    def gui_log(msg):
        if gui_log_callback:
            gui_log_callback(msg)
        logging.info(msg)

    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    gui_log("📚 开始生成小说架构")
    gui_log(f"   主题: {topic} | 类型: {genre}")
    gui_log(f"   章节数: {number_of_chapters} | 每章字数: {word_number}")
    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    # 确定总步骤数
    total_steps = 6 if num_volumes > 1 else 5

    # Step1: 核心种子
    if "core_seed_result" not in partial_data:
        gui_log(f"▶ [1/{total_steps}] 核心种子生成")
        gui_log("   ├─ 分析主题与类型...")
        logging.info("Step1: Generating core_seed_prompt (核心种子) ...")
        prompt_core = core_seed_prompt.format(
            topic=topic,
            genre=genre,
            number_of_chapters=number_of_chapters,
            word_number=word_number,
            user_guidance=user_guidance  # 修复：添加内容指导
        )
        gui_log("   ├─ 向LLM发起请求...")
        core_seed_result = invoke_with_cleaning(llm_adapter, prompt_core, system_prompt=system_prompt)
        if not core_seed_result.strip():
            gui_log("   └─ ❌ 生成失败，返回空内容")
            logging.warning("core_seed_prompt generation failed and returned empty.")
            save_partial_architecture_data(filepath, partial_data)
            return
        gui_log("   └─ ✅ 核心种子生成完成\n")
        partial_data["core_seed_result"] = core_seed_result
        save_partial_architecture_data(filepath, partial_data)
    else:
        gui_log(f"▷ [1/{total_steps}] 核心种子 (已完成，跳过)\n")
        logging.info("Step1 already done. Skipping...")

    # Step2: 角色动力学
    if "character_dynamics_result" not in partial_data:
        gui_log(f"▶ [2/{total_steps}] 角色动力学生成")
        gui_log("   ├─ 基于核心种子设计角色...")
        logging.info("Step2: Generating character_dynamics_prompt ...")
        prompt_character = character_dynamics_prompt.format(
            core_seed=partial_data["core_seed_result"].strip(),
            user_guidance=user_guidance
        )
        gui_log("   ├─ 向LLM发起请求...")
        character_dynamics_result = invoke_with_cleaning(llm_adapter, prompt_character, system_prompt=system_prompt)
        if not character_dynamics_result.strip():
            gui_log("   └─ ❌ 生成失败")
            logging.warning("character_dynamics_prompt generation failed.")
            save_partial_architecture_data(filepath, partial_data)
            return
        gui_log("   └─ ✅ 角色动力学生成完成\n")
        partial_data["character_dynamics_result"] = character_dynamics_result
        save_partial_architecture_data(filepath, partial_data)
    else:
        gui_log(f"▷ [2/{total_steps}] 角色动力学 (已完成，跳过)\n")
        logging.info("Step2 already done. Skipping...")

    # 生成初始角色状态
    if "character_dynamics_result" in partial_data and "character_state_result" not in partial_data:
        gui_log(f"▶ [3/{total_steps}] 初始角色状态生成")
        gui_log("   ├─ 基于角色动力学建立状态表...")
        logging.info("Generating initial character state from character dynamics ...")
        prompt_char_state_init = create_character_state_prompt.format(
            character_dynamics=partial_data["character_dynamics_result"].strip()
        )
        gui_log("   ├─ 向LLM发起请求...")
        character_state_init = invoke_with_cleaning(llm_adapter, prompt_char_state_init, system_prompt=system_prompt)
        if not character_state_init.strip():
            gui_log("   └─ ❌ 生成失败")
            logging.warning("create_character_state_prompt generation failed.")
            save_partial_architecture_data(filepath, partial_data)
            return
        gui_log("   ├─ 保存角色状态到 character_state.txt...")
        partial_data["character_state_result"] = character_state_init
        character_state_file = os.path.join(filepath, "character_state.txt")
        clear_file_content(character_state_file)
        save_string_to_txt(character_state_init, character_state_file)
        save_partial_architecture_data(filepath, partial_data)
        gui_log("   └─ ✅ 初始角色状态生成完成\n")
        logging.info("Initial character state created and saved.")

    # Step3: 世界观
    if "world_building_result" not in partial_data:
        gui_log(f"▶ [4/{total_steps}] 世界观构建")
        gui_log("   ├─ 构建世界观设定...")
        logging.info("Step3: Generating world_building_prompt ...")
        prompt_world = world_building_prompt.format(
            core_seed=partial_data["core_seed_result"].strip(),
            user_guidance=user_guidance  # 修复：添加用户指导
        )
        gui_log("   ├─ 向LLM发起请求...")
        world_building_result = invoke_with_cleaning(llm_adapter, prompt_world, system_prompt=system_prompt)
        if not world_building_result.strip():
            gui_log("   └─ ❌ 生成失败")
            logging.warning("world_building_prompt generation failed.")
            save_partial_architecture_data(filepath, partial_data)
            return
        gui_log("   └─ ✅ 世界观构建完成\n")
        partial_data["world_building_result"] = world_building_result
        save_partial_architecture_data(filepath, partial_data)
    else:
        gui_log(f"▷ [4/{total_steps}] 世界观 (已完成，跳过)\n")
        logging.info("Step3 already done. Skipping...")

    # Step4: 三幕式情节
    if "plot_arch_result" not in partial_data:
        gui_log(f"▶ [5/{total_steps}] 三幕式情节架构")
        gui_log("   ├─ 整合前述要素设计情节...")
        logging.info("Step4: Generating plot_architecture_prompt ...")
        prompt_plot = plot_architecture_prompt.format(
            core_seed=partial_data["core_seed_result"].strip(),
            character_dynamics=partial_data["character_dynamics_result"].strip(),
            world_building=partial_data["world_building_result"].strip(),
            user_guidance=user_guidance  # 修复：添加用户指导
        )
        gui_log("   ├─ 向LLM发起请求...")
        plot_arch_result = invoke_with_cleaning(llm_adapter, prompt_plot, system_prompt=system_prompt)
        if not plot_arch_result.strip():
            gui_log("   └─ ❌ 生成失败")
            logging.warning("plot_architecture_prompt generation failed.")
            save_partial_architecture_data(filepath, partial_data)
            return
        gui_log("   └─ ✅ 三幕式情节架构完成\n")
        partial_data["plot_arch_result"] = plot_arch_result
        save_partial_architecture_data(filepath, partial_data)
    else:
        gui_log(f"▷ [5/{total_steps}] 三幕式情节 (已完成，跳过)\n")
        logging.info("Step4 already done. Skipping...")

    core_seed_result = partial_data["core_seed_result"]
    character_dynamics_result = partial_data["character_dynamics_result"]
    world_building_result = partial_data["world_building_result"]
    plot_arch_result = partial_data["plot_arch_result"]

    final_content = (
        "#=== 0) 小说设定 ===\n"
        f"主题：{topic},类型：{genre},篇幅：约{number_of_chapters}章（每章{word_number}字）\n"
        f"分卷：{'不分卷' if num_volumes <= 1 else f'{num_volumes}卷'}\n\n"
        "#=== 1) 核心种子 ===\n"
        f"{core_seed_result}\n\n"
        "#=== 2) 角色动力学 ===\n"
        f"{character_dynamics_result}\n\n"
        "#=== 3) 世界观 ===\n"
        f"{world_building_result}\n\n"
        "#=== 4) 三幕式情节架构 ===\n"
        f"{plot_arch_result}\n"
    )

    # 保存总架构
    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    clear_file_content(arch_file)
    save_string_to_txt(final_content, arch_file)

    # Step5: 分卷规划（仅在分卷模式下执行）
    if num_volumes > 1 and "volume_arch_result" not in partial_data:
        gui_log(f"▶ [6/{total_steps}] 分卷架构规划")
        gui_log(f"   ├─ 将{number_of_chapters}章分为{num_volumes}卷...")
        logging.info(f"Step5: Generating volume architecture ({num_volumes} volumes)...")

        volume_ranges = calculate_volume_ranges(number_of_chapters, num_volumes)

        # 显示分卷范围
        for i, (vol_start, vol_end) in enumerate(volume_ranges, 1):
            chapter_count = vol_end - vol_start + 1
            gui_log(f"       第{i}卷: 第{vol_start}-{vol_end}章 (共{chapter_count}章)")

        volume_arch_result = generate_volume_architecture(
            llm_adapter=llm_adapter,
            novel_architecture=final_content,
            num_volumes=num_volumes,
            num_chapters=number_of_chapters,
            volume_ranges=volume_ranges,
            system_prompt=system_prompt,
            gui_log_callback=gui_log_callback
        )

        if not volume_arch_result.strip():
            gui_log("   └─ ⚠ 分卷架构生成失败，继续使用总架构")
            logging.warning("Volume architecture generation failed, continuing without it.")
        else:
            gui_log("   └─ ✅ 分卷架构完成\n")
            partial_data["volume_arch_result"] = volume_arch_result
            save_partial_architecture_data(filepath, partial_data)

            # 保存分卷架构到独立文件
            volume_arch_file = os.path.join(filepath, "Volume_architecture.txt")
            clear_file_content(volume_arch_file)
            save_string_to_txt(volume_arch_result, volume_arch_file)
            logging.info("Volume_architecture.txt has been generated successfully.")
    elif num_volumes > 1 and "volume_arch_result" in partial_data:
        gui_log(f"▷ [6/{total_steps}] 分卷架构 (已完成，跳过)\n")
        logging.info("Step5 (volume architecture) already done. Skipping...")

    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    gui_log("✅ 小说架构生成完毕")
    gui_log(f"   已保存至: Novel_architecture.txt")
    if num_volumes > 1:
        gui_log(f"   分卷架构: Volume_architecture.txt")
    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logging.info("Novel_architecture.txt has been generated successfully.")

    partial_arch_file = os.path.join(filepath, "partial_architecture.json")
    if os.path.exists(partial_arch_file):
        os.remove(partial_arch_file)
        logging.info("partial_architecture.json removed (all steps completed).")
