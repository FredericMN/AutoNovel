#novel_generator/finalization.py
# -*- coding: utf-8 -*-
"""
定稿章节和扩写章节（finalize_chapter、enrich_chapter_text）
"""
import os
import re  # 用于正则匹配和伏笔提取
import logging
from core.adapters.llm_adapters import create_llm_adapter
from core.adapters.embedding_adapters import create_embedding_adapter
from core.prompting.prompt_definitions import (
    summary_prompt,
    update_character_state_prompt,
    volume_summary_prompt,  # 新增：分卷总结提示词
    plot_arcs_update_prompt,  # 新增：剧情要点更新提示词
    plot_arcs_distill_prompt,  # 新增：剧情要点提炼提示词
    plot_arcs_compress_prompt,  # 新增：剧情要点压缩提示词
    plot_arcs_compress_auto_prompt,  # 🆕 剧情要点自动压缩提示词
    resolve_global_system_prompt
)
from core.prompting.prompt_manager import PromptManager  # 新增：提示词管理器
from novel_generator.common import invoke_with_cleaning
from core.utils.file_utils import read_file, clear_file_content, save_string_to_txt, get_log_file_path
from novel_generator.vectorstore_utils import update_vector_store
from core.utils.volume_utils import calculate_volume_ranges, is_volume_last_chapter  # 新增：分卷工具函数
logging.basicConfig(
    filename=get_log_file_path(),      # 日志文件名
    filemode='a',            # 追加模式（'w' 会覆盖）
    level=logging.INFO,      # 记录 INFO 及以上级别的日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
def finalize_volume(
    volume_number: int,
    volume_start: int,
    volume_end: int,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    filepath: str,
    interface_format: str,
    max_tokens: int,
    timeout: int = 600,
    use_global_system_prompt: bool = False,
    embedding_api_key: str = "",
    embedding_url: str = "",
    embedding_interface_format: str = "openai",
    embedding_model_name: str = "text-embedding-ada-002",
    gui_log_callback=None
):
    """
    为指定卷生成总结摘要（仅分卷模式）

    Args:
        volume_number: 卷号（1-based）
        volume_start: 卷的起始章节号
        volume_end: 卷的结束章节号
        embedding_api_key: Embedding API Key
        embedding_url: Embedding API URL
        embedding_interface_format: Embedding 接口格式
        embedding_model_name: Embedding 模型名称
        其他参数同 finalize_chapter

    生成文件：
        - volume_X_summary.txt: 卷摘要
        - 清空 global_summary.txt 为下一卷做准备
    """
    def gui_log(msg):
        if gui_log_callback:
            gui_log_callback(msg)
        logging.info(msg)

    # 创建提示词管理器实例（带异常保护）
    try:
        pm = PromptManager()
    except Exception as e:
        logging.error(f"Failed to initialize PromptManager: {e}")
        gui_log(f"⚠️ 提示词管理器初始化失败，将使用默认提示词: {str(e)}")

        # Fallback对象
        class FallbackPromptManager:
            def is_module_enabled(self, category, name):
                return True
            def get_prompt(self, category, name):
                return None

        pm = FallbackPromptManager()

    gui_log(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    gui_log(f"📖 开始生成第{volume_number}卷总结")
    gui_log(f"   卷范围: 第{volume_start}-{volume_end}章")
    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    # 读取该卷的所有章节内容
    chapters_dir = os.path.join(filepath, "chapters")
    volume_chapters_text = []

    gui_log(f"▶ 读取第{volume_start}-{volume_end}章内容...")
    for chap_num in range(volume_start, volume_end + 1):
        chapter_file = os.path.join(chapters_dir, f"chapter_{chap_num}.txt")
        if os.path.exists(chapter_file):
            chapter_text = read_file(chapter_file).strip()
            if chapter_text:
                volume_chapters_text.append(f"=== 第{chap_num}章 ===\n{chapter_text}")
        else:
            gui_log(f"⚠️ 第{chap_num}章文件不存在，跳过")

    if not volume_chapters_text:
        gui_log("❌ 该卷没有可用的章节内容，无法生成总结")
        logging.warning(f"Volume {volume_number} has no chapter content.")
        return

    combined_volume_text = "\n\n".join(volume_chapters_text)

    # 限制总文本长度（避免超过 context 窗口）
    max_combined_length = 150000  # 约150K字符
    if len(combined_volume_text) > max_combined_length:
        gui_log(f"⚠️ 卷内容过长({len(combined_volume_text)}字)，截取后{max_combined_length}字符")
        combined_volume_text = combined_volume_text[-max_combined_length:]

    # 读取卷架构信息
    volume_arch_file = os.path.join(filepath, "Volume_architecture.txt")
    volume_architecture_text = ""
    if os.path.exists(volume_arch_file):
        volume_architecture_text = read_file(volume_arch_file).strip()

    # 读取完整版伏笔（plot_arcs.txt，仅提取未解决部分）
    gui_log("▶ 读取本卷伏笔记录...")
    plot_arcs_file = os.path.join(filepath, "plot_arcs.txt")
    plot_arcs_text = ""

    if os.path.exists(plot_arcs_file):
        full_plot_arcs = read_file(plot_arcs_file).strip()

        if full_plot_arcs:
            # 提取未解决伏笔（排除已解决部分）
            unresolved_pattern = r'^\s*[-•·\*]?\s*\[([ABC]级[-\s]*[^\]]+)\].*'
            resolved_pattern = r'^\s*[-•·\*]?\s*[✓✅☑]\s*已解决[:：]?'

            unresolved_lines = []
            for line in full_plot_arcs.split('\n'):
                line_stripped = line.strip()
                # 匹配未解决伏笔，排除已解决伏笔
                if re.match(unresolved_pattern, line_stripped) and not re.match(resolved_pattern, line_stripped):
                    unresolved_lines.append(line_stripped)

            if unresolved_lines:
                plot_arcs_text = '\n'.join(unresolved_lines)
                gui_log(f"   └─ ✅ 已读取未解决伏笔（共{len(unresolved_lines)}条）\n")
            else:
                gui_log("   └─ ⚠️ 未发现未解决伏笔\n")
        else:
            gui_log("   └─ ⚠️ 剧情要点文件为空\n")
    else:
        gui_log("   └─ ⚠️ 剧情要点文件不存在\n")

    # 如果没有伏笔，使用占位符
    if not plot_arcs_text:
        plot_arcs_text = "（本卷暂无记录的伏笔）"

    # 构建 LLM 适配器
    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )
    system_prompt = resolve_global_system_prompt(use_global_system_prompt if use_global_system_prompt is not None else None)

    # 生成卷摘要（使用PromptManager获取提示词）
    gui_log("▶ 向LLM发起请求生成卷摘要...")

    prompt_template = pm.get_prompt("finalization", "volume_summary")
    if not prompt_template:
        gui_log("   └─ ⚠️ 提示词加载失败，使用默认提示词")
        prompt_template = volume_summary_prompt

    # 尝试使用新格式（6个参数），如果旧模板缺少占位符则回退
    try:
        volume_summary_prompt_text = prompt_template.format(
            volume_number=volume_number,
            volume_start=volume_start,
            volume_end=volume_end,
            volume_chapters_text=combined_volume_text,
            volume_architecture=volume_architecture_text,
            plot_arcs=plot_arcs_text  # 🆕 传入完整版伏笔
        )
    except KeyError as e:
        # 兼容旧版自定义模板（缺少 plot_arcs 占位符）
        gui_log(f"   │  └─ ⚠️ 自定义模板缺少占位符 {e}，使用默认模板")
        logging.warning(f"Custom prompt missing placeholder {e}, falling back to default")
        prompt_template = volume_summary_prompt  # 回退到默认
        volume_summary_prompt_text = prompt_template.format(
            volume_number=volume_number,
            volume_start=volume_start,
            volume_end=volume_end,
            volume_chapters_text=combined_volume_text,
            volume_architecture=volume_architecture_text,
            plot_arcs=plot_arcs_text
        )

    volume_summary_result = invoke_with_cleaning(
        llm_adapter,
        volume_summary_prompt_text,
        system_prompt=system_prompt
    )

    if not volume_summary_result.strip():
        gui_log("   └─ ❌ 生成失败")
        logging.warning(f"Volume {volume_number} summary generation failed.")
        return

    gui_log(f"   └─ ✅ 卷摘要生成完成 (共{len(volume_summary_result)}字)\n")

    # 保存卷摘要
    volume_summary_file = os.path.join(filepath, f"volume_{volume_number}_summary.txt")
    clear_file_content(volume_summary_file)
    save_string_to_txt(volume_summary_result, volume_summary_file)
    gui_log(f"▶ 卷摘要已保存至: volume_{volume_number}_summary.txt")

    # 🆕 附加精简版伏笔到卷摘要（确保跨卷伏笔流转）
    gui_log("▶ 检查是否有精简版伏笔需要附加...")
    global_summary_file = os.path.join(filepath, "global_summary.txt")
    if os.path.exists(global_summary_file):
        global_summary = read_file(global_summary_file)

        # 提取精简版伏笔段（使用正则匹配，支持新旧格式）
        foreshadow_match = re.search(
            r'━━━ 未解决伏笔.*?━━━\n(.*?)(?=\n\n|$)',
            global_summary,
            re.DOTALL
        )

        if foreshadow_match:
            foreshadow_content = foreshadow_match.group(1).strip()

            # 筛选A+B级伏笔（移除C级细节）
            foreshadow_lines = foreshadow_content.split('\n')
            volume_foreshadow_lines = [
                line for line in foreshadow_lines
                if line.strip() and (
                    line.strip().startswith('[A级-主线]') or
                    line.strip().startswith('[B级-支线]')
                )
            ]

            if volume_foreshadow_lines:
                # 拼接筛选后的伏笔
                volume_foreshadow = '\n'.join(volume_foreshadow_lines)

                # 读取当前卷摘要
                current_volume_summary = read_file(volume_summary_file)

                # 附加伏笔到卷摘要，使用卷专用分隔符
                volume_foreshadow_section = f"━━━ 第{volume_number}卷未解决伏笔 ━━━\n{volume_foreshadow}"
                updated_volume_summary = f"{current_volume_summary}\n\n{volume_foreshadow_section}"

                # 保存更新后的卷摘要
                clear_file_content(volume_summary_file)
                save_string_to_txt(updated_volume_summary, volume_summary_file)

                gui_log(f"   └─ ✅ A+B级伏笔已附加到卷摘要 (共{len(volume_foreshadow)}字，{len(volume_foreshadow_lines)}条)\n")
                logging.info(f"Appended A+B level plot arcs to volume {volume_number} summary")
            else:
                gui_log("   └─ ⚠️ 未发现A/B级伏笔，跳过附加\n")
        else:
            gui_log("   └─ ⚠️ 未发现精简版伏笔段，跳过附加\n")
    else:
        gui_log("   └─ ⚠️ global_summary.txt 不存在，跳过附加\n")

    # 将卷摘要也存入向量库（标记为特殊类型，方便跨卷检索）
    try:
        # 使用传入的 embedding 配置参数（复用章节写入的配置）
        embedding_adapter = create_embedding_adapter(
            embedding_interface_format,
            embedding_api_key,
            embedding_url,
            embedding_model_name
        )

        # 先删除旧的卷摘要（避免重复存储）
        from novel_generator.vectorstore_utils import delete_volume_summary_from_store
        delete_volume_summary_from_store(embedding_adapter, filepath, volume_number)
        gui_log(f"▶ 已清理旧卷摘要（如存在）")

        # 将卷摘要切分后存入向量库，标记为卷摘要类型
        from novel_generator.vectorstore_utils import update_vector_store

        # 读取更新后的卷摘要（包含精简版伏笔）
        final_volume_summary = read_file(volume_summary_file)

        # 构建卷摘要标题（便于检索时识别）
        volume_summary_with_title = f"【第{volume_number}卷总结】\n{final_volume_summary}"

        update_vector_store(
            embedding_adapter=embedding_adapter,
            new_chapter=volume_summary_with_title,
            filepath=filepath,
            chapter_num=volume_end,  # 使用卷的末章号作为标记
            volume_num=volume_number,
            doc_type="volume_summary"  # 明确标记为卷摘要
        )
        gui_log(f"▶ 卷摘要已存入向量库（便于跨卷检索）\n")
        logging.info(f"Volume {volume_number} summary stored in vector store")
    except Exception as e:
        # 非关键操作，失败不影响主流程
        logging.warning(f"Failed to store volume summary in vector store: {e}")
        gui_log(f"⚠️ 卷摘要向量存储失败（不影响主流程）: {str(e)[:50]}\n")

    # 清空全局摘要，为下一卷做准备
    global_summary_file = os.path.join(filepath, "global_summary.txt")
    clear_file_content(global_summary_file)
    gui_log("▶ 已清空 global_summary.txt，为下一卷做准备\n")

    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    gui_log(f"✅ 第{volume_number}卷总结完成")
    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logging.info(f"Volume {volume_number} summary has been generated successfully.")


def finalize_chapter(
    novel_number: int,
    word_number: int,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    filepath: str,
    embedding_api_key: str,
    embedding_url: str,
    embedding_interface_format: str,
    embedding_model_name: str,
    interface_format: str,
    max_tokens: int,
    timeout: int = 600,
    use_global_system_prompt: bool = False,
    num_volumes: int = 0,  # 新增：分卷数量
    total_chapters: int = 0,  # 新增：总章节数
    gui_log_callback=None,
    progress_callback=None  # 🆕 进度回调函数
):
    """
    对指定章节做最终处理：更新前文摘要、更新角色状态、插入向量库等。
    默认无需再做扩写操作，若有需要可在外部调用 enrich_chapter_text 处理后再定稿。

    Returns:
        bool: 定稿是否成功。True表示成功，False表示失败（如章节为空等）
    """
    # GUI日志辅助函数
    def gui_log(msg):
        if gui_log_callback:
            gui_log_callback(msg)
        logging.info(msg)

    # 进度更新辅助函数
    def update_progress(msg, pct):
        try:
            if progress_callback:
                progress_callback(msg, pct)
        except Exception as e:
            logging.warning(f"进度回调失败: {e}")

    # 定稿开始：65%
    update_progress("📝 定稿中...", 0.65)

    # 创建提示词管理器实例（带异常保护）
    try:
        pm = PromptManager()
    except Exception as e:
        logging.error(f"Failed to initialize PromptManager: {e}")
        gui_log(f"⚠️ 提示词管理器初始化失败，将使用默认提示词: {str(e)}")

        # Fallback对象
        class FallbackPromptManager:
            def is_module_enabled(self, category, name):
                return True
            def get_prompt(self, category, name):
                return None

        pm = FallbackPromptManager()

    gui_log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    gui_log(f"📝 开始定稿第{novel_number}章")
    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    chapters_dir = os.path.join(filepath, "chapters")
    chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number}.txt")
    chapter_text = read_file(chapter_file).strip()
    if not chapter_text:
        gui_log("❌ 章节文件为空，无法定稿")
        logging.warning(f"Chapter {novel_number} is empty, cannot finalize.")
        return False

    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )
    system_prompt = resolve_global_system_prompt(use_global_system_prompt if use_global_system_prompt is not None else None)

    # [1/3] 更新前文摘要（可选）
    if pm.is_module_enabled("finalization", "summary_update"):
        # 更新前文摘要：70%
        update_progress("📄 [1/3] 更新前文摘要", 0.70)
        gui_log(f"▶ [1/3] 更新前文摘要")
        gui_log("   ├─ 读取旧摘要...")
        global_summary_file = os.path.join(filepath, "global_summary.txt")
        old_global_summary = read_file(global_summary_file)

        prompt_template = pm.get_prompt("finalization", "summary_update")
        if not prompt_template:
            gui_log("   └─ ⚠️ 提示词加载失败，使用默认提示词")
            prompt_template = summary_prompt

        prompt_summary = prompt_template.format(
            chapter_text=chapter_text,
            global_summary=old_global_summary
        )
        gui_log("   ├─ 向LLM发起请求...")
        new_global_summary = invoke_with_cleaning(llm_adapter, prompt_summary, system_prompt=system_prompt)
        if not new_global_summary.strip():
            gui_log("   ├─ ⚠ 生成失败，保留旧摘要")
            new_global_summary = old_global_summary
        else:
            gui_log("   └─ ✅ 前文摘要更新完成\n")

        clear_file_content(global_summary_file)
        save_string_to_txt(new_global_summary, global_summary_file)
    else:
        gui_log(f"▷ [1/3] 更新前文摘要 (已禁用，跳过)\n")

    # [2/3] 更新角色状态（可选）
    if pm.is_module_enabled("finalization", "character_state_update"):
        # 更新角色状态：75%
        update_progress("👤 [2/3] 更新角色状态", 0.75)
        gui_log("▶ [2/3] 更新角色状态")

        # 读取旧状态
        gui_log("   ├─ 读取旧状态...")
        character_state_file = os.path.join(filepath, "character_state.txt")
        old_character_state = read_file(character_state_file)

        # 🆕 读取角色动力学（独立文件）
        gui_log("   ├─ 读取角色框架...")
        from core.utils.file_utils import read_character_dynamics
        character_dynamics = read_character_dynamics(filepath)
        if not character_dynamics:
            gui_log("   │  └─ ⚠️ 角色框架缺失，仅基于当前状态更新")

        # 🆕 读取上下文摘要（分卷兼容）
        gui_log("   ├─ 读取上下文摘要...")
        from core.utils.file_utils import get_context_summary_for_character
        context_summary = get_context_summary_for_character(
            filepath=filepath,
            chapter_num=novel_number,
            num_volumes=num_volumes,
            total_chapters=total_chapters
        )

        # 格式化提示词
        prompt_template = pm.get_prompt("finalization", "character_state_update")
        if not prompt_template:
            gui_log("   └─ ⚠️ 提示词加载失败，使用默认提示词")
            prompt_template = update_character_state_prompt

        # 🆕 尝试使用新格式（4个参数），如果旧模板缺少占位符则回退
        try:
            prompt_char_state = prompt_template.format(
                chapter_text=chapter_text,
                old_state=old_character_state,
                character_dynamics=character_dynamics,      # 🆕 传入角色框架
                context_summary=context_summary             # 🆕 传入上下文摘要
            )
        except KeyError as e:
            # 兼容旧版自定义模板（缺少新占位符）
            gui_log(f"   │  └─ ⚠️ 自定义模板缺少占位符 {e}，使用默认模板")
            logging.warning(f"Custom prompt missing placeholder {e}, falling back to default")
            prompt_template = update_character_state_prompt  # 回退到默认
            prompt_char_state = prompt_template.format(
                chapter_text=chapter_text,
                old_state=old_character_state,
                character_dynamics=character_dynamics,
                context_summary=context_summary
            )

        gui_log("   ├─ 向LLM发起请求...")
        new_char_state = invoke_with_cleaning(llm_adapter, prompt_char_state, system_prompt=system_prompt)
        if not new_char_state.strip():
            gui_log("   ├─ ⚠ 生成失败，保留旧状态")
            new_char_state = old_character_state
        else:
            gui_log("   └─ ✅ 角色状态更新完成\n")

        clear_file_content(character_state_file)
        save_string_to_txt(new_char_state, character_state_file)
    else:
        gui_log(f"▷ [2/3] 更新角色状态 (已禁用，跳过)\n")

    # [2.5/3] 更新剧情要点（详细版）
    if pm.is_module_enabled("finalization", "plot_arcs_update"):
        # 更新剧情要点：80%
        update_progress("🎭 [2.5/3] 更新剧情要点", 0.80)
        gui_log("▶ [2.5/3] 更新剧情要点（详细版）")
        gui_log("   ├─ 读取旧的剧情要点...")
        plot_arcs_file = os.path.join(filepath, "plot_arcs.txt")
        old_plot_arcs = read_file(plot_arcs_file) if os.path.exists(plot_arcs_file) else ""

        prompt_template = pm.get_prompt("finalization", "plot_arcs_update")
        if not prompt_template:
            gui_log("   └─ ⚠️ 提示词加载失败，使用默认提示词")
            prompt_template = plot_arcs_update_prompt

        prompt_plot_arcs = prompt_template.format(
            chapter_text=chapter_text,
            old_plot_arcs=old_plot_arcs if old_plot_arcs.strip() else "（暂无记录）"
        )
        gui_log("   ├─ 向LLM发起请求...")
        new_plot_arcs = invoke_with_cleaning(llm_adapter, prompt_plot_arcs, system_prompt=system_prompt)
        if not new_plot_arcs.strip():
            gui_log("   ├─ ⚠ 生成失败，保留旧内容")
            new_plot_arcs = old_plot_arcs
        else:
            gui_log("   └─ ✅ 剧情要点更新完成\n")

        clear_file_content(plot_arcs_file)
        save_string_to_txt(new_plot_arcs, plot_arcs_file)
    else:
        gui_log(f"▷ [2.5/3] 更新剧情要点 (已禁用，跳过)\n")
        new_plot_arcs = ""

    # [2.6/3] 智能压缩剧情要点（每10章自动触发）
    if pm.is_module_enabled("finalization", "plot_arcs_compress_auto"):
        # 检查是否需要压缩（每10章触发一次）
        if novel_number % 10 == 0:
            # 智能压缩：82%
            update_progress("🗜️ [2.6/3] 智能压缩剧情要点", 0.82)
            gui_log("▶ [2.6/3] 智能压缩剧情要点（周期性优化）")
            gui_log(f"   ├─ 检测到第{novel_number}章（10的倍数），触发自动压缩")

            plot_arcs_file = os.path.join(filepath, "plot_arcs.txt")
            current_plot_arcs = read_file(plot_arcs_file) if os.path.exists(plot_arcs_file) else ""

            if current_plot_arcs.strip():
                # 统计当前伏笔数量（宽松匹配，提高鲁棒性）
                # 未解决伏笔：匹配 [A级-...] 或 [B级-...] 或 [C级-...]，允许前导符号和空格
                unresolved_pattern = r'^\s*[-•·\*]?\s*\[([ABC]级[-\s]*[^\]]+)\]'
                unresolved_lines = [line for line in current_plot_arcs.split('\n')
                                   if re.match(unresolved_pattern, line.strip())]
                unresolved_count = len(unresolved_lines)

                # 已解决伏笔：匹配 ✓已解决 或 ✅已解决 或 已解决: 等变体，允许前导符号和空格
                resolved_pattern = r'^\s*[-•·\*]?\s*[✓✅☑]\s*已解决[:：]?'
                resolved_lines = [line for line in current_plot_arcs.split('\n')
                                 if re.match(resolved_pattern, line.strip())]
                resolved_count = len(resolved_lines)

                gui_log(f"   ├─ 当前状态：未解决{unresolved_count}条，已解决{resolved_count}条")

                # 判断是否需要压缩（未解决>50条 或 已解决>20条）
                if unresolved_count > 50 or resolved_count > 20:
                    gui_log("   ├─ 超过阈值，启动压缩流程...")

                    # 由于记录时已分级，直接进行智能压缩（跳过分层标记步骤）
                    gui_log("   └─ 基于已分级的伏笔进行智能压缩...")
                    compress_prompt_template = pm.get_prompt("finalization", "plot_arcs_compress_auto")
                    if not compress_prompt_template:
                        gui_log("       └─ ⚠️ 提示词加载失败，使用默认提示词")
                        compress_prompt_template = plot_arcs_compress_auto_prompt

                    compress_prompt = compress_prompt_template.format(
                        classified_plot_arcs=current_plot_arcs,  # 直接使用已分级的内容
                        current_chapter=novel_number,
                        unresolved_count=unresolved_count,
                        resolved_count=resolved_count
                    )

                    compressed_arcs = invoke_with_cleaning(llm_adapter, compress_prompt, system_prompt=system_prompt)

                    if not compressed_arcs.strip():
                        gui_log("       └─ ⚠️ 压缩失败，保留原内容")
                    else:
                        # 统计压缩后数量（宽松匹配）
                        new_unresolved = len([line for line in compressed_arcs.split('\n')
                                            if re.match(unresolved_pattern, line.strip())])
                        new_resolved = len([line for line in compressed_arcs.split('\n')
                                          if re.match(resolved_pattern, line.strip())])

                        gui_log(f"       ├─ ✅ 压缩完成：{unresolved_count}→{new_unresolved}条未解决，{resolved_count}→{new_resolved}条已解决")

                        # 保存压缩后的结果
                        clear_file_content(plot_arcs_file)
                        save_string_to_txt(compressed_arcs, plot_arcs_file)
                        gui_log("       └─ ✅ 已保存压缩后的剧情要点\n")

                        # 更新 new_plot_arcs 供后续步骤2.8使用
                        new_plot_arcs = compressed_arcs
                else:
                    gui_log("   └─ 未达到压缩阈值，跳过本次压缩\n")
            else:
                gui_log("   └─ 剧情要点文件为空，跳过压缩\n")
        # 非10的倍数章节，静默跳过（不输出日志）
    else:
        # 模块已禁用，仅在10的倍数章节输出提示
        if novel_number % 10 == 0:
            gui_log(f"▷ [2.6/3] 智能压缩剧情要点 (已禁用，跳过)\n")

    # [2.8/3] 提炼伏笔到摘要（精简版）
    if pm.is_module_enabled("finalization", "plot_arcs_distill"):
        # 提炼伏笔到摘要：85%
        update_progress("💡 [2.8/3] 提炼伏笔到摘要", 0.85)
        gui_log("▶ [2.8/3] 提炼伏笔到摘要（精简版）")

        # 只有在步骤 2.5 启用时才有内容可提炼
        if pm.is_module_enabled("finalization", "plot_arcs_update") and new_plot_arcs.strip():
            gui_log("   ├─ 从详细版提炼核心伏笔...")

            prompt_template = pm.get_prompt("finalization", "plot_arcs_distill")
            if not prompt_template:
                gui_log("   └─ ⚠️ 提示词加载失败，使用默认提示词")
                prompt_template = plot_arcs_distill_prompt

            prompt_distill = prompt_template.format(plot_arcs_text=new_plot_arcs)
            gui_log("   ├─ 向LLM发起请求...")
            distilled_arcs = invoke_with_cleaning(llm_adapter, prompt_distill, system_prompt=system_prompt)

            if distilled_arcs.strip():
                # 验证字数
                distilled_length = len(distilled_arcs)
                gui_log(f"   ├─ 精简版字数: {distilled_length}字")

                if distilled_length > 250:  # 留出50字buffer
                    gui_log(f"   ├─ ⚠️ 超过200字限制，触发二次压缩...")

                    compress_prompt_template = pm.get_prompt("finalization", "plot_arcs_compress")
                    if not compress_prompt_template:
                        compress_prompt_template = plot_arcs_compress_prompt

                    compress_prompt = compress_prompt_template.format(distilled_arcs=distilled_arcs)
                    distilled_arcs = invoke_with_cleaning(llm_adapter, compress_prompt, system_prompt=system_prompt)

                    if distilled_arcs.strip():
                        compressed_length = len(distilled_arcs)
                        gui_log(f"   ├─ 压缩后字数: {compressed_length}字")

                        # 强制截断（极端情况）
                        if compressed_length > 200:
                            distilled_arcs = distilled_arcs[:200]
                            gui_log(f"   ├─ ⚠️ 仍超限，强制截断到200字")
                    else:
                        gui_log("   ├─ ⚠️ 二次压缩失败，使用原版本")

                # 追加到 global_summary.txt
                gui_log("   ├─ 追加到前文摘要...")
                global_summary_file = os.path.join(filepath, "global_summary.txt")
                current_summary = read_file(global_summary_file) if os.path.exists(global_summary_file) else ""

                # 移除旧的伏笔部分（如果存在），支持旧格式和新格式
                current_summary = re.sub(
                    r'\n*━━━ 未解决伏笔.*?━━━\n.*?(?=\n\n|$)',
                    '',
                    current_summary,
                    flags=re.DOTALL
                ).strip()

                # 由程序添加分隔符，确保格式统一（新格式：带章节号）
                formatted_foreshadow = f"━━━ 未解决伏笔（至第{novel_number}章） ━━━\n{distilled_arcs.strip()}"

                # 追加新的伏笔（带换行隔离）
                if current_summary:
                    updated_summary = f"{current_summary}\n\n{formatted_foreshadow}"
                else:
                    updated_summary = formatted_foreshadow

                clear_file_content(global_summary_file)
                save_string_to_txt(updated_summary, global_summary_file)
                gui_log("   └─ ✅ 精简版伏笔已融入摘要\n")
            else:
                gui_log("   └─ ⚠️ 提炼失败，跳过融入摘要\n")
        else:
            if not pm.is_module_enabled("finalization", "plot_arcs_update"):
                gui_log("   └─ ⚠️ 步骤2.5已禁用，无内容可提炼\n")
            else:
                gui_log("   └─ ⚠️ 详细版剧情要点为空，跳过提炼\n")
    else:
        gui_log(f"▷ [2.8/3] 提炼伏笔到摘要 (已禁用，跳过)\n")

    # [3/3] 插入向量库：90%
    update_progress("🗄️ [3/3] 插入向量库", 0.90)
    gui_log("▶ [3/3] 插入向量库")
    gui_log("   ├─ 切分章节文本...")

    # 计算卷号（用于向量检索优化）
    volume_num = None
    if num_volumes > 1 and total_chapters > 0:
        from core.utils.volume_utils import get_volume_number, calculate_volume_ranges
        volume_ranges = calculate_volume_ranges(total_chapters, num_volumes)
        volume_num = get_volume_number(novel_number, volume_ranges)
        gui_log(f"   ├─ 章节元数据: chapter={novel_number}, volume={volume_num}")

    update_vector_store(
        embedding_adapter=create_embedding_adapter(
            embedding_interface_format,
            embedding_api_key,
            embedding_url,
            embedding_model_name
        ),
        new_chapter=chapter_text,
        filepath=filepath,
        chapter_num=novel_number,  # 新增：章节号
        volume_num=volume_num,  # 新增：卷号
        doc_type="chapter"  # 明确标记为章节
    )
    gui_log("   └─ ✅ 向量库更新完成\n")

    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    gui_log(f"✅ 第{novel_number}章定稿完成")
    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logging.info(f"Chapter {novel_number} has been finalized.")

    # 检查是否需要生成卷总结（分卷模式 + 卷末章节 + 模块已启用）
    if num_volumes > 1 and total_chapters > 0 and pm.is_module_enabled("finalization", "volume_summary"):
        volume_ranges = calculate_volume_ranges(total_chapters, num_volumes)

        if is_volume_last_chapter(novel_number, volume_ranges):
            # 生成卷总结：95%
            update_progress("📚 生成卷总结", 0.95)
            from core.utils.volume_utils import get_volume_number

            volume_num = get_volume_number(novel_number, volume_ranges)
            if volume_num > 0:
                vol_start, vol_end = volume_ranges[volume_num - 1]

                gui_log(f"\n🔔 检测到第{novel_number}章是第{volume_num}卷的最后一章")
                gui_log("   启动卷总结生成流程...\n")

                finalize_volume(
                    volume_number=volume_num,
                    volume_start=vol_start,
                    volume_end=vol_end,
                    api_key=api_key,
                    base_url=base_url,
                    model_name=model_name,
                    temperature=temperature,
                    filepath=filepath,
                    interface_format=interface_format,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    use_global_system_prompt=use_global_system_prompt,
                    embedding_api_key=embedding_api_key,
                    embedding_url=embedding_url,
                    embedding_interface_format=embedding_interface_format,
                    embedding_model_name=embedding_model_name,
                    gui_log_callback=gui_log_callback
                )
    elif num_volumes > 1 and total_chapters > 0 and not pm.is_module_enabled("finalization", "volume_summary"):
        # 卷总结已禁用，检查是否是卷末章节并提示
        volume_ranges = calculate_volume_ranges(total_chapters, num_volumes)
        if is_volume_last_chapter(novel_number, volume_ranges):
            from core.utils.volume_utils import get_volume_number
            volume_num = get_volume_number(novel_number, volume_ranges)
            gui_log(f"\n🔔 第{novel_number}章是第{volume_num}卷的最后一章")
            gui_log("   卷总结模块已禁用，跳过生成\n")

    # 定稿完成：100%
    update_progress("🎉 完成", 1.0)

    return True  # 定稿成功

def enrich_chapter_text(
    chapter_text: str,
    word_number: int,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    interface_format: str,
    max_tokens: int,
    timeout: int = 600,
    use_global_system_prompt: bool = False
) -> str:
    """
    对章节文本进行扩写，使其更接近 word_number 字数，保持剧情连贯。
    """
    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )
    system_prompt = resolve_global_system_prompt(use_global_system_prompt if use_global_system_prompt is not None else None)
    prompt = f"""以下章节文本较短，请在保持剧情连贯的前提下进行扩写，使其更充实，接近 {word_number} 字左右，仅给出最终文本，不要解释任何内容。：
原内容：
{chapter_text}
"""
    enriched_text = invoke_with_cleaning(llm_adapter, prompt, system_prompt=system_prompt)
    return enriched_text if enriched_text else chapter_text








