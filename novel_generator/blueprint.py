#novel_generator/blueprint.py
# -*- coding: utf-8 -*-
"""
章节蓝图生成（Chapter_blueprint_generate 及辅助函数）
"""
import os
import re
import logging
from novel_generator.common import invoke_with_cleaning
from llm_adapters import create_llm_adapter
from prompt_definitions import (
    chapter_blueprint_prompt,
    chunked_chapter_blueprint_prompt,
    volume_chapter_blueprint_prompt,  # 新增：分卷蓝图提示词
    resolve_global_system_prompt
)
from utils import read_file, clear_file_content, save_string_to_txt
from volume_utils import calculate_volume_ranges  # 新增：分卷工具函数
logging.basicConfig(
    filename='app.log',      # 日志文件名
    filemode='a',            # 追加模式（'w' 会覆盖）
    level=logging.INFO,      # 记录 INFO 及以上级别的日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
def compute_chunk_size(number_of_chapters: int, max_tokens: int) -> int:
    """
    基于“每章约100 tokens”的粗略估算，
    再结合当前max_tokens，计算分块大小：
      chunk_size = (floor(max_tokens/100/10)*10) - 10
    并确保 chunk_size 不会小于1或大于实际章节数。
    """
    tokens_per_chapter = 200.0
    ratio = max_tokens / tokens_per_chapter
    ratio_rounded_to_10 = int(ratio // 10) * 10
    chunk_size = ratio_rounded_to_10 - 10
    if chunk_size < 1:
        chunk_size = 1
    if chunk_size > number_of_chapters:
        chunk_size = number_of_chapters
    return chunk_size

def limit_chapter_blueprint(blueprint_text: str, limit_chapters: int = 100) -> str:
    """
    从已有章节目录中只取最近的 limit_chapters 章，以避免 prompt 超长。
    """
    pattern = r"(第\s*\d+\s*章.*?)(?=第\s*\d+\s*章|$)"
    chapters = re.findall(pattern, blueprint_text, flags=re.DOTALL)
    if not chapters:
        return blueprint_text
    if len(chapters) <= limit_chapters:
        return blueprint_text
    selected = chapters[-limit_chapters:]
    return "\n\n".join(selected).strip()

def Chapter_blueprint_generate(
    interface_format: str,
    api_key: str,
    base_url: str,
    llm_model: str,
    filepath: str,
    number_of_chapters: int,
    num_volumes: int = 0,  # 新增：分卷数量
    user_guidance: str = "",
    use_global_system_prompt: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    timeout: int = 600,
    gui_log_callback=None
) -> None:
    """
    章节蓝图生成主函数，支持分卷模式和非分卷模式。

    分卷模式 (num_volumes > 1)：
      - 读取 Volume_architecture.txt
      - 按卷逐个生成章节蓝图
      - 使用 volume_chapter_blueprint_prompt

    非分卷模式 (num_volumes <= 1)：
      - 若章节数 <= chunk_size，直接一次性生成
      - 若章节数 > chunk_size，进行分块生成
      - 支持断点续传

    生成完成后输出至 Novel_directory.txt。
    """
    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    if not os.path.exists(arch_file):
        logging.warning("Novel_architecture.txt not found. Please generate architecture first.")
        return

    architecture_text = read_file(arch_file).strip()
    if not architecture_text:
        logging.warning("Novel_architecture.txt is empty.")
        return

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
    gui_log("📖 开始生成章节蓝图")
    gui_log(f"   目标章节数: {number_of_chapters}")
    if num_volumes > 1:
        gui_log(f"   分卷模式: {num_volumes}卷")
    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    filename_dir = os.path.join(filepath, "Novel_directory.txt")
    if not os.path.exists(filename_dir):
        open(filename_dir, "w", encoding="utf-8").close()

    existing_blueprint = read_file(filename_dir).strip()

    # ============ 分卷模式：按卷生成 ============
    if num_volumes > 1:
        volume_arch_file = os.path.join(filepath, "Volume_architecture.txt")
        if not os.path.exists(volume_arch_file):
            gui_log("❌ 错误：分卷模式下需要先生成 Volume_architecture.txt")
            logging.error("Volume mode enabled but Volume_architecture.txt not found.")
            return

        volume_architecture_text = read_file(volume_arch_file).strip()
        if not volume_architecture_text:
            gui_log("❌ 错误：Volume_architecture.txt 为空")
            logging.error("Volume_architecture.txt is empty.")
            return

        gui_log(f"▶ 分卷模式：将为 {num_volumes} 卷生成章节蓝图\n")

        volume_ranges = calculate_volume_ranges(number_of_chapters, num_volumes)
        final_blueprint = existing_blueprint

        # 检测已完成的章节
        max_existing_chap = 0
        if existing_blueprint:
            pattern = r"第\s*(\d+)\s*章"
            existing_chapter_numbers = re.findall(pattern, existing_blueprint)
            existing_chapter_numbers = [int(x) for x in existing_chapter_numbers if x.isdigit()]
            max_existing_chap = max(existing_chapter_numbers) if existing_chapter_numbers else 0
            gui_log(f"▷ 检测到已有蓝图内容，已完成到第{max_existing_chap}章")

        # 按卷生成
        for vol_idx, (vol_start, vol_end) in enumerate(volume_ranges, 1):
            # 跳过已完成的卷
            if max_existing_chap >= vol_end:
                gui_log(f"▷ [卷{vol_idx}] 第{vol_start}-{vol_end}章 已完成，跳过\n")
                continue

            # 部分完成的卷：调整起始章节
            actual_start = max(vol_start, max_existing_chap + 1)
            vol_chapter_count = vol_end - actual_start + 1

            gui_log(f"▶ [卷{vol_idx}/{num_volumes}] 生成第{actual_start}-{vol_end}章 (共{vol_chapter_count}章)")
            gui_log(f"   ├─ 构建分卷提示词...")

            # 读取前序卷摘要（用于保持设定一致性，避免细节漂移）
            previous_volumes_summary = ""
            if vol_idx > 1:
                for i in range(1, vol_idx):
                    summary_file = os.path.join(filepath, f"volume_{i}_summary.txt")
                    if os.path.exists(summary_file):
                        prev_vol_summary = read_file(summary_file).strip()
                        if prev_vol_summary:
                            previous_volumes_summary += f"═══ 第{i}卷实际发展 ═══\n{prev_vol_summary}\n\n"

                # 降级策略：如果前序卷摘要不存在，尝试使用 global_summary
                if not previous_volumes_summary:
                    global_summary_file = os.path.join(filepath, "global_summary.txt")
                    if os.path.exists(global_summary_file):
                        global_summary_content = read_file(global_summary_file).strip()
                        if global_summary_content:
                            previous_volumes_summary = f"前序剧情摘要（全局）：\n{global_summary_content}"
                            gui_log(f"   ├─ ⚠ 前序卷摘要不存在，使用全局摘要降级")

            volume_prompt = volume_chapter_blueprint_prompt.format(
                novel_architecture=architecture_text,
                volume_architecture=volume_architecture_text,
                volume_number=vol_idx,
                volume_start=actual_start,
                volume_end=vol_end,
                volume_chapter_count=vol_chapter_count,
                previous_volumes_summary=previous_volumes_summary,  # 新增
                user_guidance=user_guidance
            )

            gui_log(f"   ├─ 向LLM发起请求...")
            logging.info(f"Generating blueprint for Volume {vol_idx} (chapters {actual_start}-{vol_end})...")

            volume_blueprint_result = invoke_with_cleaning(llm_adapter, volume_prompt, system_prompt=system_prompt)

            if not volume_blueprint_result.strip():
                gui_log(f"   └─ ❌ 第{vol_idx}卷蓝图生成失败\n")
                logging.warning(f"Volume {vol_idx} blueprint generation failed.")
                # 保存已有内容
                clear_file_content(filename_dir)
                save_string_to_txt(final_blueprint.strip(), filename_dir)
                return

            gui_log(f"   └─ ✅ 第{vol_idx}卷蓝图生成完成\n")

            # 拼接蓝图
            if final_blueprint.strip():
                final_blueprint += "\n\n" + volume_blueprint_result.strip()
            else:
                final_blueprint = volume_blueprint_result.strip()

            # 实时保存
            clear_file_content(filename_dir)
            save_string_to_txt(final_blueprint.strip(), filename_dir)
            logging.info(f"Volume {vol_idx} blueprint saved.")

        gui_log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        gui_log("✅ 分卷章节蓝图全部生成完毕")
        gui_log(f"   已保存至: Novel_directory.txt")
        gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logging.info("Volume-based chapter blueprint generation completed.")
        return

    # ============ 非分卷模式：原有逻辑 ============
    chunk_size = compute_chunk_size(number_of_chapters, max_tokens)
    gui_log(f"▶ 分块大小计算: 每次生成 {chunk_size} 章")
    logging.info(f"Number of chapters = {number_of_chapters}, computed chunk_size = {chunk_size}.")

    if existing_blueprint:
        gui_log("▷ 检测到已有蓝图内容，从断点继续生成")
        logging.info("Detected existing blueprint content. Will resume chunked generation from that point.")
        pattern = r"第\s*(\d+)\s*章"
        existing_chapter_numbers = re.findall(pattern, existing_blueprint)
        existing_chapter_numbers = [int(x) for x in existing_chapter_numbers if x.isdigit()]
        max_existing_chap = max(existing_chapter_numbers) if existing_chapter_numbers else 0
        gui_log(f"   已完成章节: 第1-{max_existing_chap}章")
        logging.info(f"Existing blueprint indicates up to chapter {max_existing_chap} has been generated.")
        final_blueprint = existing_blueprint
        current_start = max_existing_chap + 1
        total_chunks = ((number_of_chapters - max_existing_chap) + chunk_size - 1) // chunk_size
        chunk_index = 0
        while current_start <= number_of_chapters:
            chunk_index += 1
            current_end = min(current_start + chunk_size - 1, number_of_chapters)
            gui_log(f"\n▶ [{chunk_index}/{total_chunks}] 生成第{current_start}-{current_end}章...")
            limited_blueprint = limit_chapter_blueprint(final_blueprint, 100)
            chunk_prompt = chunked_chapter_blueprint_prompt.format(
                novel_architecture=architecture_text,
                chapter_list=limited_blueprint,
                number_of_chapters=number_of_chapters,
                n=current_start,
                m=current_end,
                user_guidance=user_guidance  # 新增参数
            )
            gui_log(f"   ├─ 向LLM发起请求...")
            logging.info(f"Generating chapters [{current_start}..{current_end}] in a chunk...")
            chunk_result = invoke_with_cleaning(llm_adapter, chunk_prompt, system_prompt=system_prompt)
            if not chunk_result.strip():
                gui_log(f"   └─ ❌ 生成失败")
                logging.warning(f"Chunk generation for chapters [{current_start}..{current_end}] is empty.")
                clear_file_content(filename_dir)
                save_string_to_txt(final_blueprint.strip(), filename_dir)
                return
            gui_log(f"   └─ ✅ 第{current_start}-{current_end}章完成")
            final_blueprint += "\n\n" + chunk_result.strip()
            clear_file_content(filename_dir)
            save_string_to_txt(final_blueprint.strip(), filename_dir)
            current_start = current_end + 1

        gui_log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        gui_log("✅ 章节蓝图全部生成完毕")
        gui_log(f"   已保存至: Novel_directory.txt")
        gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logging.info("All chapters blueprint have been generated (resumed chunked).")
        return

    if chunk_size >= number_of_chapters:
        gui_log("▶ 章节数量适中，一次性生成所有章节...")
        prompt = chapter_blueprint_prompt.format(
            novel_architecture=architecture_text,
            number_of_chapters=number_of_chapters,
            user_guidance=user_guidance  # 新增参数
        )
        gui_log("   ├─ 向LLM发起请求...")
        blueprint_text = invoke_with_cleaning(llm_adapter, prompt, system_prompt=system_prompt)
        if not blueprint_text.strip():
            gui_log("   └─ ❌ 生成失败")
            logging.warning("Chapter blueprint generation result is empty.")
            return

        clear_file_content(filename_dir)
        save_string_to_txt(blueprint_text, filename_dir)
        gui_log("   └─ ✅ 所有章节蓝图生成完成")
        gui_log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        gui_log("✅ 章节蓝图全部生成完毕")
        gui_log(f"   已保存至: Novel_directory.txt")
        gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logging.info("Novel_directory.txt (chapter blueprint) has been generated successfully (single-shot).")
        return

    gui_log("▶ 章节数量较多，启动分块生成模式...")
    logging.info("Will generate chapter blueprint in chunked mode from scratch.")
    final_blueprint = ""
    current_start = 1
    total_chunks = (number_of_chapters + chunk_size - 1) // chunk_size
    chunk_index = 0
    while current_start <= number_of_chapters:
        chunk_index += 1
        current_end = min(current_start + chunk_size - 1, number_of_chapters)
        gui_log(f"\n▶ [{chunk_index}/{total_chunks}] 生成第{current_start}-{current_end}章...")
        limited_blueprint = limit_chapter_blueprint(final_blueprint, 100)
        chunk_prompt = chunked_chapter_blueprint_prompt.format(
            novel_architecture=architecture_text,
            chapter_list=limited_blueprint,
            number_of_chapters=number_of_chapters,
            n=current_start,
            m=current_end,
            user_guidance=user_guidance  # 新增参数
        )
        gui_log(f"   ├─ 向LLM发起请求...")
        logging.info(f"Generating chapters [{current_start}..{current_end}] in a chunk...")
        chunk_result = invoke_with_cleaning(llm_adapter, chunk_prompt, system_prompt=system_prompt)
        if not chunk_result.strip():
            gui_log(f"   └─ ❌ 生成失败")
            logging.warning(f"Chunk generation for chapters [{current_start}..{current_end}] is empty.")
            clear_file_content(filename_dir)
            save_string_to_txt(final_blueprint.strip(), filename_dir)
            return
        gui_log(f"   └─ ✅ 第{current_start}-{current_end}章完成")
        if final_blueprint.strip():
            final_blueprint += "\n\n" + chunk_result.strip()
        else:
            final_blueprint = chunk_result.strip()
        clear_file_content(filename_dir)
        save_string_to_txt(final_blueprint.strip(), filename_dir)
        current_start = current_end + 1

    gui_log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    gui_log("✅ 章节蓝图全部生成完毕")
    gui_log(f"   已保存至: Novel_directory.txt")
    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logging.info("Novel_directory.txt (chapter blueprint) has been generated successfully (chunked).")
