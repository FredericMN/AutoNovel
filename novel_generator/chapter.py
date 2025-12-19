# novel_generator/chapter.py
# -*- coding: utf-8 -*-
"""
章节草稿生成及获取历史章节文本、当前章节摘要等
"""
import os
import json
import logging
import re  # 添加re模块导入
from core.adapters.llm_adapters import create_llm_adapter
from core.prompting.prompt_definitions import (
    first_chapter_draft_prompt,  # 用于 fallback
    next_chapter_draft_prompt,  # 用于 fallback
    summarize_recent_chapters_prompt,  # 用于 fallback
    knowledge_filter_prompt,  # 用于 fallback
    knowledge_search_prompt,  # 用于 fallback
    chapter_critique_prompt,  # 🆕 批评家提示词
    chapter_refine_prompt,    # 🆕 作家重写提示词
    resolve_global_system_prompt
)
from core.prompting.prompt_manager import PromptManager  # 新增：提示词管理器
from core.utils.chapter_directory_parser import get_chapter_info_from_blueprint
from novel_generator.common import invoke_with_cleaning
from core.utils.file_utils import read_file, clear_file_content, save_string_to_txt, save_data_to_json, get_log_file_path
from novel_generator.vectorstore_utils import load_vector_store
from core.utils.volume_utils import (
    get_volume_number,
    is_volume_last_chapter,
    calculate_volume_ranges  # 优化：统一导入，避免动态导入
)

def extract_volume_architecture(volume_arch_text: str, target_volume_num: int) -> str:
    """
    从 Volume_architecture.txt 中提取指定卷的架构信息

    Args:
        volume_arch_text: Volume_architecture.txt 的完整内容
        target_volume_num: 目标卷号（1-based）

    Returns:
        str: 该卷的架构文本，如果未找到则返回空字符串

    支持格式：
        ### **第一卷（第1-10章）**
        ### **第1卷（第1-10章）**
        ## 第二卷
        ### 第三卷
    """
    import re

    # 分割文本为卷块（通过标题行分割）
    # 优化正则：匹配行首的标题格式，排除内容中的引用
    # 必须以 # 或 * 开头，确保是 Markdown 标题
    # 支持格式: ### **第一卷（第1-10章）** 等
    volume_header_pattern = re.compile(
        r'^[#*]+\s*\**\s*第\s*([零〇一二两三四五六七八九十百千万\d]+)\s*卷',
        re.MULTILINE
    )

    matches = list(volume_header_pattern.finditer(volume_arch_text))
    if not matches:
        logging.warning("Volume_architecture.txt 中未找到卷标题")
        logging.debug(f"文件内容前500字符: {volume_arch_text[:500]}")
        return ""

    logging.info(f"找到{len(matches)}个卷标题标记")

    # 转换中文数字
    from core.utils.chapter_directory_parser import _to_int_from_chinese

    for i, match in enumerate(matches):
        vol_num_str = match.group(1)
        # 尝试数字转换
        if vol_num_str.isdigit():
            vol_num = int(vol_num_str)
        else:
            vol_num = _to_int_from_chinese(vol_num_str)

        logging.debug(f"解析到卷号: '{vol_num_str}' -> {vol_num}, 目标: {target_volume_num}")

        if vol_num == target_volume_num:
            # 找到目标卷，提取从当前位置到下一个卷标题（或文件末尾）的内容
            start_pos = match.start()

            # 查找分隔符 "---" 或下一个卷标题
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(volume_arch_text)

            # 提取内容
            content = volume_arch_text[start_pos:end_pos].strip()

            # 移除开头和结尾的分隔符 "---"（支持前后都有的情况）
            content = re.sub(r'^[\s\n]*-{3,}[\s\n]*', '', content)  # 移除开头
            content = re.sub(r'[\s\n]*-{3,}[\s\n]*$', '', content)  # 移除结尾
            content = content.strip()

            if content:
                logging.info(f"成功提取第{target_volume_num}卷架构，长度: {len(content)}字符")
            else:
                logging.warning(f"第{target_volume_num}卷架构提取后为空")
            return content

    logging.warning(f"Volume_architecture.txt 中未找到第{target_volume_num}卷")
    return ""


logging.basicConfig(
    filename=get_log_file_path(),      # 日志文件名
    filemode='a',            # 追加模式（'w' 会覆盖）
    level=logging.INFO,      # 记录 INFO 及以上级别的日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_volume_context(
    filepath: str,
    novel_number: int,
    num_volumes: int,
    total_chapters: int  # 新增：实际总章节数
) -> dict:
    """
    获取当前章节的分卷上下文信息

    Args:
        filepath: 小说保存路径
        novel_number: 当前章节号
        num_volumes: 总卷数（0或1表示不分卷）
        total_chapters: 实际总章节数

    Returns:
        dict: 分卷上下文信息
        {
            "is_volume_mode": bool,           # 是否分卷模式
            "volume_number": int,             # 当前卷号（1-based）
            "is_volume_first_chapter": bool,  # 是否卷的第一章
            "is_volume_last_chapter": bool,   # 是否卷的最后一章
            "volume_summary": str,            # 前一卷的摘要（如果存在）
            "current_volume_summary": str     # 当前卷的摘要（如果已完成部分章节）
        }
    """
    # 非分卷模式
    if num_volumes <= 1:
        return {
            "is_volume_mode": False,
            "volume_number": 0,
            "is_volume_first_chapter": False,
            "is_volume_last_chapter": False,
            "volume_summary": "",
            "current_volume_summary": ""
        }

    # 分卷模式
    volume_ranges = calculate_volume_ranges(total_chapters, num_volumes)
    volume_num = get_volume_number(novel_number, volume_ranges)

    if volume_num == 0:
        logging.warning(f"Chapter {novel_number} not found in volume ranges.")
        return {
            "is_volume_mode": True,
            "volume_number": 0,
            "is_volume_first_chapter": False,
            "is_volume_last_chapter": False,
            "volume_summary": "",
            "current_volume_summary": ""
        }

    vol_start, vol_end = volume_ranges[volume_num - 1]
    is_first = (novel_number == vol_start)
    is_last = is_volume_last_chapter(novel_number, volume_ranges)

    # 读取前一卷摘要
    prev_volume_summary = ""
    if volume_num > 1:
        prev_vol_summary_file = os.path.join(filepath, f"volume_{volume_num - 1}_summary.txt")
        if os.path.exists(prev_vol_summary_file):
            prev_volume_summary = read_file(prev_vol_summary_file).strip()
        else:
            # 降级策略：如果前一卷摘要不存在，使用全局摘要
            logging.warning(f"前一卷摘要文件不存在，尝试使用全局摘要降级")
            global_summary_file = os.path.join(filepath, "global_summary.txt")
            if os.path.exists(global_summary_file):
                prev_volume_summary = read_file(global_summary_file).strip()
                logging.info("已使用 global_summary.txt 作为前一卷摘要的降级替代")

    # 读取当前卷摘要（如果卷已经完成并生成了摘要）
    current_vol_summary = ""
    current_vol_summary_file = os.path.join(filepath, f"volume_{volume_num}_summary.txt")
    if os.path.exists(current_vol_summary_file):
        current_vol_summary = read_file(current_vol_summary_file).strip()

    return {
        "is_volume_mode": True,
        "volume_number": volume_num,
        "is_volume_first_chapter": is_first,
        "is_volume_last_chapter": is_last,
        "volume_summary": prev_volume_summary,
        "current_volume_summary": current_vol_summary
    }

def extract_key_plot_arcs(filepath: str) -> str:
    """
    [Plan A] 从 plot_arcs.txt 中提取 A级(主线)和 B级(支线)的未解决伏笔

    格式兼容性：
    - 支持任意前导符号：-, •, ·, *, 数字编号等
    - 支持任意缩进
    - 支持 [A级-xxx] 或 【A级-xxx】 格式
    - 自动排除已解决的伏笔（通过检查同行的解决标记）
    """
    plot_arcs_file = os.path.join(filepath, "plot_arcs.txt")
    if not os.path.exists(plot_arcs_file):
        return "（暂无记录）"

    full_content = read_file(plot_arcs_file)
    if not full_content.strip():
        return "（暂无记录）"

    # 提取未解决部分
    unresolved_lines = []

    # 更宽松的正则匹配：任意位置匹配 [A级-xxx] 或 【A级-xxx】
    # 格式示例: [A级-主线] xxxx、【B级-支线】xxx、1. [A级-主线] xxx
    pattern = r'[\[【]([AB]级-[^\]】]+)[\]】]'

    # 已解决标记：支持多种符号和格式
    resolved_markers = ['✓已解决', '✅已解决', '☑已解决', '已解决', '（已解决）', '(已解决)', '[已解决]']

    for line in full_content.split('\n'):
        line_stripped = line.strip()
        if not line_stripped:
            continue

        # 检查本行是否包含已解决标记
        is_resolved = any(marker in line_stripped for marker in resolved_markers)
        if is_resolved:
            continue

        # 使用 search 而非 match，匹配行内任意位置的 A/B 级标记
        if re.search(pattern, line_stripped):
            unresolved_lines.append(line_stripped)

    if not unresolved_lines:
        return "（暂无重要未解决伏笔）"

    # 限制返回条数，避免过长（A级最多10条，B级最多5条）
    a_level = [l for l in unresolved_lines if re.search(r'[\[【]A级', l)]
    b_level = [l for l in unresolved_lines if re.search(r'[\[【]B级', l)]

    result_lines = a_level[:10] + b_level[:5]

    if not result_lines:
        return "（暂无重要未解决伏笔）"

    logging.debug(f"Extracted {len(a_level)} A-level and {len(b_level)} B-level plot arcs")
    return "\n".join(result_lines)

def get_last_n_chapters_text(chapters_dir: str, current_chapter_num: int, n: int = 3) -> list:
    """
    [Plan B] 获取最近n章内容，采用混合模式：
    - N-1章：优先读取原文 (保持文风连贯)
    - N-2, N-3...章：优先读取摘要 (chapter_X_summary.txt)，减少token消耗
    """
    texts = []
    start_chap = max(1, current_chapter_num - n)

    for c in range(start_chap, current_chapter_num):
        is_prev_chapter = (c == current_chapter_num - 1)

        # 尝试读取摘要（非上一章时优先）
        summary_file = os.path.join(chapters_dir, f"chapter_{c}_summary.txt")
        chap_file = os.path.join(chapters_dir, f"chapter_{c}.txt")

        text_content = ""
        source_type = ""

        # 策略：
        # 1. 如果是上一章 (N-1)，强制读原文（除非原文不存在）
        if is_prev_chapter:
            if os.path.exists(chap_file):
                text_content = read_file(chap_file).strip()
                source_type = "RAW"
            elif os.path.exists(summary_file):
                text_content = read_file(summary_file).strip()
                source_type = "SUMMARY_FALLBACK"
        # 2. 如果是更早的章节 (N-2, N-3...)，优先读摘要
        else:
            if os.path.exists(summary_file):
                text_content = read_file(summary_file).strip()
                source_type = "SUMMARY"
            elif os.path.exists(chap_file):
                text_content = read_file(chap_file).strip()
                source_type = "RAW_FALLBACK"

        if text_content:
            # 区分不同来源的标记方式
            if source_type == "SUMMARY":
                texts.append(f"【第{c}章摘要】\n{text_content}")
                logging.debug(f"Loaded summary for chapter {c}")
            elif source_type == "SUMMARY_FALLBACK":
                # 上一章的原文不存在，降级使用摘要，添加特殊标记
                texts.append(f"【第{c}章（仅摘要可用）】\n{text_content}")
                logging.debug(f"Loaded summary (fallback) for chapter {c}")
            else:
                # RAW 或 RAW_FALLBACK：直接使用原文
                texts.append(text_content)
                logging.debug(f"Loaded raw text for chapter {c}")
        else:
            texts.append("")

    return texts

def summarize_recent_chapters(
    interface_format: str,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
    chapters_text_list: list,
    novel_number: int,            # 新增参数
    chapter_info: dict,           # 新增参数
    next_chapter_info: dict,      # 新增参数
    timeout: int = 600,
    system_prompt: str = ""
) -> str:  # 修改返回值类型为 str，不再是 tuple
    """
    根据前三章内容生成当前章节的精准摘要。
    增强容错:空值兜底、格式化失败重试、使用章节目录作为后备。
    """
    try:
        combined_text = "\n".join(chapters_text_list).strip()
        if not combined_text:
            logging.warning("No previous chapters found, using chapter directory as fallback")
            # 空值兜底:使用章节目录信息生成简要说明
            chapter_info = chapter_info or {}
            return f"当前为第{novel_number}章,前文尚无内容。本章将围绕「{chapter_info.get('chapter_title', '未命名')}」展开,核心目标是{chapter_info.get('chapter_purpose', '推进剧情')}。"

        # 限制组合文本长度
        max_combined_length = 4000
        if len(combined_text) > max_combined_length:
            combined_text = combined_text[-max_combined_length:]

        llm_adapter = create_llm_adapter(
            interface_format=interface_format,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )

        # 确保所有参数都有默认值
        chapter_info = chapter_info or {}
        next_chapter_info = next_chapter_info or {}

        # 从 PromptManager 动态加载提示词（带异常保护）
        try:
            pm = PromptManager()
        except Exception as e:
            logging.error(f"Failed to initialize PromptManager in summarize_recent_chapters: {e}")
            pm = None

        if pm:
            summary_prompt_template = pm.get_prompt("chapter", "chapter_summary")
        else:
            summary_prompt_template = None

        if not summary_prompt_template:
            logging.warning("Chapter summary prompt not found, using default")
            summary_prompt_template = summarize_recent_chapters_prompt

        prompt = summary_prompt_template.format(
            combined_text=combined_text,
            novel_number=novel_number,
            chapter_title=chapter_info.get("chapter_title", "未命名"),
            chapter_role=chapter_info.get("chapter_role", "常规章节"),
            chapter_purpose=chapter_info.get("chapter_purpose", "内容推进"),
            suspense_level=chapter_info.get("suspense_level", "中等"),
            foreshadowing=chapter_info.get("foreshadowing", "无"),
            plot_twist_level=chapter_info.get("plot_twist_level", "★☆☆☆☆"),
            chapter_summary=chapter_info.get("chapter_summary", ""),
            next_chapter_number=novel_number + 1,
            next_chapter_title=next_chapter_info.get("chapter_title", "（未命名）"),
            next_chapter_role=next_chapter_info.get("chapter_role", "过渡章节"),
            next_chapter_purpose=next_chapter_info.get("chapter_purpose", "承上启下"),
            next_chapter_summary=next_chapter_info.get("chapter_summary", "衔接过渡内容"),
            next_chapter_suspense_level=next_chapter_info.get("suspense_level", "中等"),
            next_chapter_foreshadowing=next_chapter_info.get("foreshadowing", "无特殊伏笔"),
            next_chapter_plot_twist_level=next_chapter_info.get("plot_twist_level", "★☆☆☆☆")
        )

        active_system_prompt = system_prompt.strip()

        # 第一次尝试生成摘要
        response_text = invoke_with_cleaning(
            llm_adapter,
            prompt,
            system_prompt=active_system_prompt
        )
        summary = extract_summary_from_response(response_text)

        if not summary or len(summary) < 50:
            logging.warning(f"First attempt summary too short ({len(summary) if summary else 0} chars), retrying with simplified prompt")

            # 重试:使用简化的提示词
            simplified_prompt = f"""请为以下前文内容生成一个简洁的摘要(300-800字)：

前文内容：
{combined_text}

当前要写的是第{novel_number}章《{chapter_info.get('chapter_title', '未命名')}》。

请直接输出摘要内容,不需要任何前缀标记。"""

            retry_response = invoke_with_cleaning(
                llm_adapter,
                simplified_prompt,
                system_prompt=active_system_prompt
            )

            # 重试响应也需要经过格式清洗
            if retry_response:
                retry_summary = extract_summary_from_response(retry_response)
                # 如果提取成功且比第一次好，则使用重试结果
                if retry_summary and len(retry_summary) >= 50:
                    summary = retry_summary
                    logging.info(f"Retry successful, extracted {len(summary)} chars")
                elif retry_summary:
                    # 提取结果仍然太短，但比原来好
                    summary = retry_summary
                    logging.warning(f"Retry summary still short ({len(retry_summary)} chars) but using it")
                # 如果提取完全失败，保持第一次的结果不变
                else:
                    logging.warning("Retry extraction failed, keeping first attempt result")

        if not summary:
            logging.error("Failed to generate summary after retry, using fallback")
            # 最终兜底:使用章节目录信息
            fallback_summary = f"前文已完成{len(chapters_text_list)}章内容。"
            if chapter_info.get("chapter_summary"):
                fallback_summary += f"接下来第{novel_number}章的核心内容是:{chapter_info.get('chapter_summary')}"
            return fallback_summary

        return summary[:2000]  # 限制摘要长度

    except Exception as e:
        logging.error(f"Error in summarize_recent_chapters: {str(e)}")
        # 异常兜底
        chapter_info = chapter_info or {}
        return f"[摘要生成异常] 第{novel_number}章《{chapter_info.get('chapter_title', '未命名')}》,将基于前文继续创作。"

def extract_summary_from_response(response_text: str) -> str:
    """
    从响应文本中提取摘要部分,增强容错能力

    支持多种格式:
    - 标准格式: "当前章节摘要: xxx"
    - Markdown格式: "**摘要**: xxx" 或 "### 摘要"
    - 带装饰: "【摘要】xxx" 或 "━━摘要━━"
    """
    if not response_text:
        return ""

    # 清理常见的markdown标记
    cleaned = response_text.strip()

    # 移除代码块标记
    if cleaned.startswith("```"):
        parts = cleaned.split("```")
        if len(parts) >= 3:
            cleaned = parts[1]  # 取中间内容

    # 定义多种摘要标记,按优先级排序
    summary_markers = [
        # 标准中文标记
        ("当前章节摘要:", "当前章节摘要："),
        ("章节摘要:", "章节摘要："),
        ("本章摘要:", "本章摘要："),
        ("摘要:", "摘要："),

        # Markdown格式
        ("**当前章节摘要**:", "**当前章节摘要**："),
        ("**章节摘要**:", "**章节摘要**："),
        ("**摘要**:", "**摘要**："),
        ("### 当前章节摘要", "### 章节摘要", "### 摘要"),
        ("## 当前章节摘要", "## 章节摘要", "## 摘要"),

        # 带装饰符号
        ("【当前章节摘要】", "【章节摘要】", "【摘要】"),
        ("━━当前章节摘要━━", "━━章节摘要━━", "━━摘要━━"),
        ("「当前章节摘要」", "「章节摘要」", "「摘要」"),
    ]

    # 尝试匹配所有标记
    for markers in summary_markers:
        if isinstance(markers, str):
            markers = (markers,)

        for marker in markers:
            if marker in cleaned:
                parts = cleaned.split(marker, 1)
                if len(parts) > 1:
                    extracted = parts[1].strip()

                    # 移除可能的尾部标记
                    for end_marker in ["```", "---", "***", "━━━"]:
                        if end_marker in extracted:
                            extracted = extracted.split(end_marker)[0].strip()

                    # 移除开头的冒号或空白
                    extracted = extracted.lstrip("：: \n\t")

                    if extracted:
                        logging.info(f"Successfully extracted summary using marker: {marker}")
                        return extracted

    # 如果所有标记都失败,尝试启发式提取
    # 1. 查找第一个"。"之后的长文本块(可能是摘要)
    lines = cleaned.split('\n')
    potential_summary = []
    found_content = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 跳过明显的标题行
        if line.startswith('#') or line.startswith('**'):
            continue

        # 跳过过短的行(可能是标题)
        if len(line) < 20:
            continue

        # 找到实质内容
        if len(line) >= 50 and '。' in line:
            found_content = True
            potential_summary.append(line)
        elif found_content:
            # 继续收集相邻行
            potential_summary.append(line)
            if len('\n'.join(potential_summary)) > 500:
                break

    if potential_summary:
        extracted = '\n'.join(potential_summary)
        logging.warning(f"Used heuristic extraction, found {len(extracted)} chars")
        return extracted

    # 最后兜底:返回原文(会在调用处截断)
    logging.warning("No marker matched, returning original response")
    return cleaned

def format_chapter_info(chapter_info: dict) -> str:
    """将章节信息字典格式化为文本"""
    template = """
章节编号：第{number}章
章节标题：《{title}》
章节定位：{role}
核心作用：{purpose}
主要人物：{characters}
关键道具：{items}
场景地点：{location}
伏笔设计：{foreshadow}
悬念密度：{suspense}
转折程度：{twist}
章节简述：{summary}
"""
    return template.format(
        number=chapter_info.get('chapter_number', '未知'),
        title=chapter_info.get('chapter_title', '未知'),
        role=chapter_info.get('chapter_role', '未知'),
        purpose=chapter_info.get('chapter_purpose', '未知'),
        characters=chapter_info.get('characters_involved', '未指定'),
        items=chapter_info.get('key_items', '未指定'),
        location=chapter_info.get('scene_location', '未指定'),
        foreshadow=chapter_info.get('foreshadowing', '无'),
        suspense=chapter_info.get('suspense_level', '一般'),
        twist=chapter_info.get('plot_twist_level', '★☆☆☆☆'),
        summary=chapter_info.get('chapter_summary', '未提供')
    )

def parse_search_keywords(response_text: str) -> list:
    """
    解析检索关键词，支持多种格式并提供兜底策略

    标准格式：'科技公司·数据泄露\n地下实验室·基因编辑'
    兜底支持：
    - 空格分隔："科技公司 数据泄露"
    - 顿号分隔："科技公司、数据泄露"
    - 连字符："科技公司-数据泄露"
    - 纯文本行（作为单个关键词组）

    Returns:
        list: 关键词组列表，最多5组，空响应返回空列表
    """
    if not response_text or not response_text.strip():
        logging.warning("parse_search_keywords: Empty response, returning empty list")
        return []

    response_text = response_text.strip()

    # 策略1: 标准格式 - 包含中文间隔号·的行
    keywords = [
        line.strip().replace('·', ' ')
        for line in response_text.split('\n')
        if '·' in line and line.strip()
    ][:5]

    if keywords:
        logging.info(f"parse_search_keywords: Extracted {len(keywords)} keywords using standard format (·)")
        return keywords

    # 策略2: 兜底格式1 - 包含其他分隔符（、- : |）
    fallback_separators = ['、', '-', ':', '|']
    for sep in fallback_separators:
        keywords = [
            line.strip().replace(sep, ' ')
            for line in response_text.split('\n')
            if sep in line and line.strip()
        ][:5]

        if keywords:
            logging.warning(f"parse_search_keywords: Using fallback separator '{sep}', extracted {len(keywords)} keywords")
            return keywords

    # 策略3: 兜底格式2 - 按行分割（每行作为一个关键词组）
    lines = [line.strip() for line in response_text.split('\n') if line.strip()]

    # 过滤掉明显不是关键词的行（如标题、说明文字）
    # 放宽长度限制，允许2字符短关键词（如"AI""VR""秦朝"）
    valid_lines = []
    filtered_lines = []  # 记录被过滤的行

    for line in lines:
        # 允许长度2-50的行
        if not (2 <= len(line) <= 50):
            filtered_lines.append((line, "length"))
            continue

        # 排除明显的标题和说明文字
        if line.startswith(('注', '说明', '备注', '#', '*', '提示', '关键词', '检索')):
            filtered_lines.append((line, "prefix"))
            continue

        if line.endswith(('：', ':')):
            filtered_lines.append((line, "suffix"))
            continue

        valid_lines.append(line)

    # 记录被过滤的行到日志（仅记录前3个，避免日志过长）
    if filtered_lines:
        sample = filtered_lines[:3]
        logging.debug(f"parse_search_keywords: Filtered {len(filtered_lines)} lines, sample: {sample}")

    if valid_lines:
        keywords = valid_lines[:5]
        logging.warning(f"parse_search_keywords: Using line-based fallback, extracted {len(keywords)} keywords")
        return keywords

    # 策略4: 最终兜底 - 使用整个响应作为单个关键词（截断到合理长度）
    if len(response_text) <= 100:
        logging.error(f"parse_search_keywords: All parsing strategies failed, using entire response as single keyword: '{response_text[:50]}...'")
        return [response_text]
    else:
        # 响应过长，可能是LLM输出了段落而非关键词，记录错误并返回空
        logging.error(f"parse_search_keywords: Response too long ({len(response_text)} chars) and no valid format detected. Response preview: '{response_text[:100]}...'")
        return []

def extract_chapter_numbers(text: str) -> list:
    """
    从文本中提取章节编号

    支持格式：
    - 第N章 / 第 N 章（允许空格）
    - chapter_N / chapter N / Chapter N（允许空格和下划线，不区分大小写）
    """
    # 匹配"第N章"格式（允许空格）
    if re.search(r'第\s*\d+\s*章', text):
        return list(map(int, re.findall(r'第\s*(\d+)\s*章', text)))

    # 匹配"chapter N"格式（允许空格/下划线，不区分大小写）
    elif re.search(r'chapter[_\s]*\d+', text, re.IGNORECASE):
        return list(map(int, re.findall(r'chapter[_\s]*(\d+)', text, re.IGNORECASE)))

    # 兜底:尝试提取所有数字（但要谨慎，可能误匹配）
    nums = [int(s) for s in re.findall(r'\d+', text) if s.isdigit()]
    if nums:
        logging.debug(f"extract_chapter_numbers fallback: extracted {nums} from text: {text[:50]}...")
    return nums

def apply_unified_content_rules(texts: list, current_chapter: int) -> list:
    """
    统一的内容分类与规则处理函数,合并原 apply_content_rules 和 apply_knowledge_rules 逻辑。

    Args:
        texts: 待处理的文本列表
        current_chapter: 当前章节号

    Returns:
        处理后的文本列表,带有规则标记
    """
    processed = []

    for text in texts:
        # 检测是否包含历史章节标记（更严格的正则）
        has_chapter_marker = (
            re.search(r'第\s*\d+\s*章', text) or  # "第N章"格式，允许空格
            re.search(r'chapter[_\s]*\d+', text, re.IGNORECASE)  # "chapter_N"或"chapter N"，不区分大小写
        )

        if has_chapter_marker:
            # 提取章节编号
            chap_nums = extract_chapter_numbers(text)

            if chap_nums:
                recent_chap = max(chap_nums)
                time_distance = current_chapter - recent_chap

                # 根据时间距离应用不同规则
                if time_distance <= 2:
                    # 近2章:直接跳过,防止重复
                    processed.append(f"[SKIP] 跳过近章内容({time_distance}章距离): {text[:120]}...")
                    logging.info(f"Skipped recent chapter content (distance={time_distance}): {text[:50]}...")

                elif time_distance <= 3:
                    # 第3章:需要高度修改
                    processed.append(f"[HISTORY_LIMIT] 近期章节限制(需修改≥50%): {text[:100]}...")
                    logging.debug(f"Marked as HISTORY_LIMIT (distance={time_distance})")

                elif time_distance <= 5:
                    # 3-5章前:允许引用但需要修改
                    processed.append(f"[HISTORY_REF] 历史参考(需改写≥40%): {text}")
                    logging.debug(f"Marked as HISTORY_REF (distance={time_distance})")

                else:
                    # 6章以前:可以引用核心概念
                    processed.append(f"[HISTORY_OK] 远期章节(可引用核心): {text}")
                    logging.debug(f"Marked as HISTORY_OK (distance={time_distance})")
            else:
                # 无法提取章节号,但有章节标记,保守处理
                processed.append(f"[HISTORY_UNKNOWN] 历史内容(章节号不明): {text[:100]}...")
                logging.warning(f"Chapter marker found but no valid chapter number: {text[:50]}...")
        else:
            # 非历史章节内容,判断为外部知识,优先使用
            processed.append(f"[EXTERNAL] 外部知识(优先使用): {text}")
            logging.debug(f"Marked as EXTERNAL knowledge: {text[:50]}...")

    return processed

def get_filtered_knowledge_context(
    api_key: str,
    base_url: str,
    model_name: str,
    interface_format: str,
    embedding_adapter,
    filepath: str,
    chapter_info: dict,
    retrieved_texts: list,
    max_tokens: int = 2048,
    timeout: int = 600,
    system_prompt: str = ""
) -> str:
    """
    优化后的知识过滤处理

    注意：retrieved_texts 应该是已经过 apply_unified_content_rules 处理的文本列表
    """
    if not retrieved_texts:
        return "（无相关知识库内容）"

    try:
        # 直接使用已处理的文本，不再重复调用规则函数
        processed_texts = retrieved_texts

        llm_adapter = create_llm_adapter(
            interface_format=interface_format,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            temperature=0.3,
            max_tokens=max_tokens,
            timeout=timeout
        )

        # 限制检索文本长度并格式化
        formatted_texts = []
        max_text_length = 600
        for i, text in enumerate(processed_texts, 1):
            if len(text) > max_text_length:
                text = text[:max_text_length] + "..."
            formatted_texts.append(f"[预处理结果{i}]\n{text}")

        # 使用格式化函数处理章节信息
        formatted_chapter_info = (
            f"当前章节定位：{chapter_info.get('chapter_role', '')}\n"
            f"核心目标：{chapter_info.get('chapter_purpose', '')}\n"
            f"关键要素：{chapter_info.get('characters_involved', '')} | "
            f"{chapter_info.get('key_items', '')} | "
            f"{chapter_info.get('scene_location', '')}"
        )

        # 从 PromptManager 动态加载提示词（带异常保护）
        try:
            pm = PromptManager()
        except Exception as e:
            logging.error(f"Failed to initialize PromptManager in filter_knowledge_context: {e}")
            pm = None

        if pm:
            filter_prompt_template = pm.get_prompt("helper", "knowledge_filter")
        else:
            filter_prompt_template = None

        if not filter_prompt_template:
            logging.warning("Knowledge filter prompt not found, using default")
            filter_prompt_template = knowledge_filter_prompt

        prompt = filter_prompt_template.format(
            chapter_info=formatted_chapter_info,
            retrieved_texts="\n\n".join(formatted_texts) if formatted_texts else "（无检索结果）"
        )

        filtered_content = invoke_with_cleaning(llm_adapter, prompt, system_prompt=system_prompt)
        return filtered_content if filtered_content else "（知识内容过滤失败）"

    except TimeoutError as e:
        # 超时异常
        import traceback
        logging.error(f"Knowledge filtering timeout after {timeout}s: {str(e)}\n{traceback.format_exc()}")
        return "（知识过滤超时，建议增加timeout参数或检查网络连接）"

    except Exception as e:
        # 其他异常：API认证、模型错误、参数错误等
        import traceback
        error_msg = str(e).lower()
        error_details = traceback.format_exc()

        # 记录完整堆栈到日志
        logging.error(f"Error in knowledge filtering: {str(e)}\n{error_details}")

        # 根据错误类型返回不同提示
        if "api" in error_msg and ("key" in error_msg or "auth" in error_msg or "unauthorized" in error_msg):
            return "（API认证失败，请检查api_key配置是否正确）"

        elif "connection" in error_msg or "network" in error_msg or "unreachable" in error_msg:
            return "（网络连接失败，请检查base_url和网络状态）"

        elif "rate" in error_msg and "limit" in error_msg:
            return "（API调用频率超限，请稍后重试或升级配额）"

        elif "model" in error_msg and ("not found" in error_msg or "invalid" in error_msg):
            return f"（模型不可用，请检查model_name配置: {model_name}）"

        elif "token" in error_msg and ("limit" in error_msg or "exceed" in error_msg):
            return "（Token数量超限，请减少max_tokens或简化输入内容）"

        else:
            # 未知错误，返回前100字符的错误信息
            error_preview = str(e)[:100]
            return f"（内容过滤出错：{error_preview}{'...' if len(str(e)) > 100 else ''}）"

def build_chapter_prompt(
    api_key: str,
    base_url: str,
    model_name: str,
    filepath: str,
    novel_number: int,
    word_number: int,
    temperature: float,
    user_guidance: str,
    characters_involved: str,
    key_items: str,
    scene_location: str,
    time_constraint: str,
    embedding_api_key: str,
    embedding_url: str,
    embedding_interface_format: str,
    embedding_model_name: str,
    embedding_retrieval_k: int = 2,
    interface_format: str = "openai",
    max_tokens: int = 2048,
    timeout: int = 600,
    system_prompt: str = "",
    num_volumes: int = 0,  # 新增：分卷数量
    total_chapters: int = 0,  # 新增：总章节数
    gui_log_callback=None,
    progress_callback=None  # 🆕 进度回调函数
) -> str:
    """
    构造当前章节的请求提示词（完整实现版）
    修改重点：
    1. 优化知识库检索流程
    2. 新增内容重复检测机制
    3. 集成提示词应用规则
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

    # 阶段1开始：0% - 📂 准备中
    update_progress("📂 准备中...", 0.0)

    # 读取基础文件：5%
    update_progress("📖 读取基础文件", 0.05)
    arch_file = os.path.join(filepath, "Novel_architecture.txt")
    novel_architecture_text = read_file(arch_file)
    directory_file = os.path.join(filepath, "Novel_directory.txt")
    blueprint_text = read_file(directory_file)
    global_summary_file = os.path.join(filepath, "global_summary.txt")
    global_summary_text = read_file(global_summary_file)
    character_state_file = os.path.join(filepath, "character_state.txt")
    character_state_text = read_file(character_state_file)

    # [Plan A] 读取关键剧情伏笔
    unresolved_plot_arcs = extract_key_plot_arcs(filepath)
    if unresolved_plot_arcs and unresolved_plot_arcs != "（暂无记录）":
        logging.info(f"Injecting {len(unresolved_plot_arcs.splitlines())} unresolved plot arcs into prompt")
    else:
        unresolved_plot_arcs = "（暂无明确记录）"

    # 获取章节信息
    chapter_info = get_chapter_info_from_blueprint(blueprint_text, novel_number)
    chapter_title = chapter_info["chapter_title"]
    chapter_role = chapter_info["chapter_role"]
    chapter_purpose = chapter_info["chapter_purpose"]
    suspense_level = chapter_info["suspense_level"]
    foreshadowing = chapter_info["foreshadowing"]
    plot_twist_level = chapter_info["plot_twist_level"]
    chapter_summary = chapter_info["chapter_summary"]
    volume_position = chapter_info.get("volume_position", "")  # 🆕 新增：提取卷内位置

    # 提取卷信息（新增）
    current_vol_num = chapter_info.get("volume_number")
    current_vol_title = chapter_info.get("volume_title", "")

    # 读取当前卷架构信息（新增）
    current_volume_architecture = ""

    # 优化判断逻辑：即使 current_vol_num 为空，也尝试根据 num_volumes 推断
    if num_volumes > 1:
        volume_arch_file = os.path.join(filepath, "Volume_architecture.txt")
        if os.path.exists(volume_arch_file):
            volume_arch_text = read_file(volume_arch_file).strip()

            # 如果章节信息中没有卷号，尝试根据章节号推断
            if not current_vol_num:
                volume_ranges = calculate_volume_ranges(total_chapters, num_volumes)
                current_vol_num = get_volume_number(novel_number, volume_ranges)
                logging.info(f"章节 {novel_number} 根据范围推断卷号为: {current_vol_num}")

            # 提取当前卷的架构信息
            if current_vol_num:
                current_volume_architecture = extract_volume_architecture(
                    volume_arch_text,
                    current_vol_num
                )
                if current_volume_architecture:
                    logging.info(f"成功为第{novel_number}章提取第{current_vol_num}卷架构")
                else:
                    logging.warning(f"第{novel_number}章提取第{current_vol_num}卷架构失败")
            else:
                logging.warning(f"无法确定第{novel_number}章的卷号,跳过卷架构提取")
        else:
            logging.warning(f"分卷模式已启用但 Volume_architecture.txt 不存在: {volume_arch_file}")

    # 获取下一章节信息
    next_chapter_number = novel_number + 1
    next_chapter_info = get_chapter_info_from_blueprint(blueprint_text, next_chapter_number)
    next_chapter_title = next_chapter_info.get("chapter_title", "（未命名）")
    next_chapter_role = next_chapter_info.get("chapter_role", "过渡章节")
    next_chapter_purpose = next_chapter_info.get("chapter_purpose", "承上启下")
    next_chapter_suspense = next_chapter_info.get("suspense_level", "中等")
    next_chapter_foreshadow = next_chapter_info.get("foreshadowing", "无特殊伏笔")
    next_chapter_twist = next_chapter_info.get("plot_twist_level", "★☆☆☆☆")
    next_chapter_summary = next_chapter_info.get("chapter_summary", "衔接过渡内容")

    # 提取下一章卷信息（新增）
    next_vol_num = next_chapter_info.get("volume_number")
    next_vol_title = next_chapter_info.get("volume_title", "")

    # 构建卷信息展示字符串（新增）
    if current_vol_num and current_vol_title:
        current_volume_display = f"第{current_vol_num}卷：{current_vol_title}"
    else:
        current_volume_display = ""

    if next_vol_num and next_vol_title:
        next_volume_display = f"第{next_vol_num}卷：{next_vol_title}"
    else:
        next_volume_display = ""

    # 创建章节目录
    chapters_dir = os.path.join(filepath, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)

    # 第一章特殊处理
    if novel_number == 1:
        # 从 PromptManager 动态加载提示词（带异常保护）
        try:
            pm = PromptManager()
        except Exception as e:
            logging.error(f"Failed to initialize PromptManager in build_first_chapter_prompt: {e}")
            pm = None

        if pm:
            first_prompt_template = pm.get_prompt("chapter", "first_chapter")
        else:
            first_prompt_template = None

        if not first_prompt_template:
            logging.warning("First chapter prompt not found, using default")
            first_prompt_template = first_chapter_draft_prompt

        return first_prompt_template.format(
            volume_display=current_volume_display,  # 新增：传递卷信息
            volume_architecture=current_volume_architecture,  # 新增：传递卷架构
            novel_number=novel_number,
            word_number=word_number,
            chapter_title=chapter_title,
            chapter_role=chapter_role,
            chapter_purpose=chapter_purpose,
            suspense_level=suspense_level,
            foreshadowing=foreshadowing,
            plot_twist_level=plot_twist_level,
            volume_position=volume_position,  # 🆕 新增：传递卷内位置
            chapter_summary=chapter_summary,
            characters_involved=characters_involved,
            key_items=key_items,
            scene_location=scene_location,
            time_constraint=time_constraint,
            user_guidance=user_guidance,
            novel_setting=novel_architecture_text,
            unresolved_plot_arcs=unresolved_plot_arcs  # 🆕 注入伏笔
        )

    # 获取前文内容和摘要
    recent_texts = get_last_n_chapters_text(chapters_dir, novel_number, n=3)

    # 获取分卷上下文
    volume_context = get_volume_context(filepath, novel_number, num_volumes, total_chapters)

    # 构建分卷信息字符串
    volume_info_text = ""
    if volume_context["is_volume_mode"]:
        vol_num = volume_context["volume_number"]
        volume_info_parts = [f"当前卷号：第{vol_num}卷"]

        if volume_context["is_volume_first_chapter"]:
            volume_info_parts.append("章节定位：本卷首章")
        elif volume_context["is_volume_last_chapter"]:
            volume_info_parts.append("章节定位：本卷末章（需为本卷收尾）")

        volume_info_text = "\n".join(volume_info_parts)

        # 新策略：固定传递"上一卷完整摘要 + 本卷累积摘要"
        # 优势：保证跨卷连贯性，避免过早丢失前一卷信息
        if volume_context["volume_summary"]:
            # 构建摘要：上一卷 + 本卷
            combined_summary = f"【上一卷完整回顾】\n{volume_context['volume_summary']}\n\n"

            # 添加本卷累积摘要
            if global_summary_text.strip():
                combined_summary += f"【本卷进展】\n{global_summary_text}"
            else:
                combined_summary += "【本卷进展】\n（本卷尚未开始累积摘要）"

            global_summary_text = combined_summary
            logging.info(f"第{novel_number}章使用固定策略: 上一卷完整摘要 + 本卷累积摘要")
        else:
            # 第一卷或无前卷摘要：仅使用本卷累积
            logging.info(f"第{novel_number}章使用本卷累积摘要（无前卷信息）")

        # 否则继续使用全局摘要（默认）
    else:
        # 非分卷模式：不显示分卷信息
        volume_info_text = ""

    # 生成前文摘要：10%
    update_progress("📝 生成前文摘要", 0.10)
    try:
        logging.info("Attempting to generate summary")
        short_summary = summarize_recent_chapters(
            interface_format=interface_format,
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            chapters_text_list=recent_texts,
            novel_number=novel_number,
            chapter_info=chapter_info,
            next_chapter_info=next_chapter_info,
            timeout=timeout,
            system_prompt=system_prompt
        )
        logging.info("Summary generated successfully")
    except Exception as e:
        logging.error(f"Error in summarize_recent_chapters: {str(e)}")
        short_summary = "（摘要生成失败）"

    # 获取前一章结尾
    previous_excerpt = ""
    for text in reversed(recent_texts):
        if text.strip():
            previous_excerpt = text[-800:] if len(text) > 800 else text
            break

    # 缓存本章上下文（供 Plan C 重写使用，避免重复计算）
    if novel_number > 1:
        context_cache = {
            "novel_number": novel_number,
            "short_summary": short_summary,
            "previous_chapter_excerpt": previous_excerpt
        }
        context_cache_file = os.path.join(chapters_dir, f"chapter_{novel_number}_context.json")
        try:
            save_data_to_json(context_cache, context_cache_file)
            logging.info(f"Saved Plan C context cache: {context_cache_file}")
        except Exception as e:
            logging.warning(f"Failed to save Plan C context cache: {e}")

    # 知识库检索和处理
    try:
        gui_log("\n━━━━ 知识库检索 ━━━━")
        gui_log("▶ 开始向量检索流程...")

        # 生成检索关键词：15%
        update_progress("🔍 生成检索关键词", 0.15)
        gui_log("   ├─ 生成检索关键词...")
        llm_adapter = create_llm_adapter(
            interface_format=interface_format,
            base_url=base_url,
            model_name=model_name,
            api_key=api_key,
            temperature=0.3,
            max_tokens=max_tokens,
            timeout=timeout
        )

        # 从 PromptManager 动态加载提示词（带异常保护）
        try:
            pm = PromptManager()
        except Exception as e:
            logging.error(f"Failed to initialize PromptManager in build_next_chapter_prompt (knowledge search): {e}")
            pm = None

        if pm:
            search_prompt_template = pm.get_prompt("helper", "knowledge_search")
        else:
            search_prompt_template = None

        if not search_prompt_template:
            logging.warning("Knowledge search prompt not found, using default")
            search_prompt_template = knowledge_search_prompt

        search_prompt = search_prompt_template.format(
            chapter_number=novel_number,
            chapter_title=chapter_title,
            characters_involved=characters_involved,
            key_items=key_items,
            scene_location=scene_location,
            chapter_role=chapter_role,
            chapter_purpose=chapter_purpose,
            foreshadowing=foreshadowing,
            short_summary=short_summary,
            user_guidance=user_guidance,
            time_constraint=time_constraint
        )

        search_response = invoke_with_cleaning(llm_adapter, search_prompt, system_prompt=system_prompt)
        keyword_groups = parse_search_keywords(search_response)

        if keyword_groups:
            gui_log(f"   ├─ 生成关键词组: {len(keyword_groups)}组")
            for idx, kw in enumerate(keyword_groups, 1):
                gui_log(f"       {idx}. {kw}")
        else:
            gui_log("   ├─ ⚠ 未能生成关键词，跳过检索")

        # 执行向量检索(使用去重优化的批量检索)：20%
        update_progress("🗂️ 执行向量检索", 0.20)
        from core.adapters.embedding_adapters import create_embedding_adapter
        from novel_generator.vectorstore_utils import get_relevant_contexts_deduplicated

        embedding_adapter = create_embedding_adapter(
            embedding_interface_format,
            embedding_api_key,
            embedding_url,
            embedding_model_name
        )

        gui_log("   ├─ 执行向量检索...")
        # 使用新的去重检索函数（支持分卷检索）
        retrieved_docs = get_relevant_contexts_deduplicated(
            embedding_adapter=embedding_adapter,
            query_groups=keyword_groups,
            filepath=filepath,
            k_per_group=embedding_retrieval_k,
            max_total_results=embedding_retrieval_k * len(keyword_groups) if keyword_groups else 10,
            current_chapter=novel_number,  # 新增：当前章节号
            num_volumes=num_volumes,  # 新增：总卷数
            total_chapters=total_chapters  # 新增：总章节数
        )

        # 记录检索统计
        from novel_generator.vectorstore_monitor import log_retrieval

        gui_log(f"   ├─ 检索结果: 共{len(retrieved_docs)}条文档")

        # 统计文档类型
        type_counts = {}
        for doc_info in retrieved_docs:
            doc_type = doc_info.get("type", "Unknown")
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1

        if type_counts:
            gui_log("   ├─ 文档类型分布:")
            for doc_type, count in type_counts.items():
                gui_log(f"       · {doc_type}: {count}条")

        for keyword_group in keyword_groups:
            # 为每个关键词组找到所有命中的文档
            docs_for_group = [
                {"content": d["content"], "type": d["type"]}
                for d in retrieved_docs
                if keyword_group in d.get("queries", [])
            ]
            log_retrieval(
                filepath=filepath,
                query=keyword_group,
                retrieved_docs=docs_for_group,
                chapter_number=novel_number
            )

        # 格式化检索结果
        all_contexts = []
        for doc_info in retrieved_docs:
            content = doc_info["content"]
            doc_type = doc_info["type"]
            all_contexts.append(f"[{doc_type}] {content}")

        # 应用统一的内容规则：25%
        update_progress("🔧 应用内容过滤规则", 0.25)
        gui_log("   ├─ 应用内容过滤规则...")
        processed_contexts = apply_unified_content_rules(all_contexts, novel_number)

        # 统计过滤结果
        skip_count = sum(1 for ctx in processed_contexts if ctx.startswith("[SKIP]"))
        external_count = sum(1 for ctx in processed_contexts if ctx.startswith("[EXTERNAL]"))
        history_count = len(processed_contexts) - skip_count - external_count

        gui_log(f"   ├─ 过滤统计:")
        gui_log(f"       · 跳过近章内容: {skip_count}条")
        gui_log(f"       · 外部知识: {external_count}条")
        gui_log(f"       · 历史参考: {history_count}条")

        # 执行知识过滤：30%
        update_progress("🧠 LLM二次过滤与整合", 0.30)
        gui_log("   ├─ LLM二次过滤与整合...")
        chapter_info_for_filter = {
            "chapter_number": novel_number,
            "chapter_title": chapter_title,
            "chapter_role": chapter_role,
            "chapter_purpose": chapter_purpose,
            "characters_involved": characters_involved,
            "key_items": key_items,
            "scene_location": scene_location,
            "foreshadowing": foreshadowing,  # 修复拼写错误
            "suspense_level": suspense_level,
            "plot_twist_level": plot_twist_level,
            "chapter_summary": chapter_summary,
            "time_constraint": time_constraint
        }
        
        filtered_context = get_filtered_knowledge_context(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            interface_format=interface_format,
            embedding_adapter=embedding_adapter,
            filepath=filepath,
            chapter_info=chapter_info_for_filter,
            retrieved_texts=processed_contexts,
            max_tokens=max_tokens,
            timeout=timeout,
            system_prompt=system_prompt
        )

        # 统计最终使用的知识
        final_length = len(filtered_context)
        gui_log(f"   └─ ✅ 知识整合完成 (输出{final_length}字)")
        gui_log("━━━━━━━━━━━━━━━━━━━━\n")

    except Exception as e:
        gui_log(f"   └─ ❌ 知识检索异常: {str(e)[:100]}")
        gui_log("━━━━━━━━━━━━━━━━━━━━\n")
        logging.error(f"知识处理流程异常：{str(e)}")
        filtered_context = "（知识库处理失败）"

    # 从 PromptManager 动态加载提示词（带异常保护）
    try:
        pm = PromptManager()
    except Exception as e:
        logging.error(f"Failed to initialize PromptManager in build_next_chapter_prompt (final): {e}")
        pm = None

    if pm:
        next_prompt_template = pm.get_prompt("chapter", "next_chapter")
    else:
        next_prompt_template = None

    if not next_prompt_template:
        logging.warning("Next chapter prompt not found, using default")
        next_prompt_template = next_chapter_draft_prompt

    # 提示词构建完成：35%
    update_progress("✅ 提示词构建完成", 0.35)

    # 返回最终提示词
    return next_prompt_template.format(
        user_guidance=user_guidance if user_guidance else "无特殊指导",
        global_summary=global_summary_text,
        volume_info=volume_info_text,  # 新增：分卷信息
        volume_architecture=current_volume_architecture,  # 新增：卷架构
        previous_chapter_excerpt=previous_excerpt,
        character_state=character_state_text,
        short_summary=short_summary,
        novel_number=novel_number,
        chapter_title=chapter_title,
        chapter_role=chapter_role,
        chapter_purpose=chapter_purpose,
        suspense_level=suspense_level,
        foreshadowing=foreshadowing,
        plot_twist_level=plot_twist_level,
        volume_position=volume_position,  # 🆕 新增：传递卷内位置
        chapter_summary=chapter_summary,
        word_number=word_number,
        characters_involved=characters_involved,
        key_items=key_items,
        scene_location=scene_location,
        time_constraint=time_constraint,
        current_volume_display=current_volume_display,  # 新增：当前卷展示
        next_chapter_number=next_chapter_number,
        next_chapter_title=next_chapter_title,
        next_chapter_role=next_chapter_role,
        next_chapter_purpose=next_chapter_purpose,
        next_chapter_suspense_level=next_chapter_suspense,
        next_chapter_foreshadowing=next_chapter_foreshadow,
        next_chapter_plot_twist_level=next_chapter_twist,
        next_chapter_summary=next_chapter_summary,
        next_volume_display=next_volume_display,  # 新增：下一章卷展示
        filtered_context=filtered_context,
        unresolved_plot_arcs=unresolved_plot_arcs  # 🆕 注入伏笔
    )

def generate_chapter_draft(
    api_key: str,
    base_url: str,
    model_name: str,
    filepath: str,
    novel_number: int,
    word_number: int,
    temperature: float,
    user_guidance: str,
    characters_involved: str,
    key_items: str,
    scene_location: str,
    time_constraint: str,
    embedding_api_key: str,
    embedding_url: str,
    embedding_interface_format: str,
    embedding_model_name: str,
    embedding_retrieval_k: int = 2,
    interface_format: str = "openai",
    max_tokens: int = 2048,
    timeout: int = 600,
    custom_prompt_text: str = None,
    use_global_system_prompt: bool = False,
    num_volumes: int = 0,  # 新增：分卷数量
    total_chapters: int = 0,  # 新增：总章节数
    gui_log_callback=None
) -> str:
    """
    生成章节草稿，支持自定义提示词
    """
    # GUI日志辅助函数
    def gui_log(msg):
        if gui_log_callback:
            gui_log_callback(msg)
        logging.info(msg)

    gui_log(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    gui_log(f"📝 开始生成第{novel_number}章草稿")
    gui_log(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    system_prompt = resolve_global_system_prompt(use_global_system_prompt if use_global_system_prompt is not None else None)

    if custom_prompt_text is None:
        prompt_text = build_chapter_prompt(
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            filepath=filepath,
            novel_number=novel_number,
            word_number=word_number,
            temperature=temperature,
            user_guidance=user_guidance,
            characters_involved=characters_involved,
            key_items=key_items,
            scene_location=scene_location,
            time_constraint=time_constraint,
            embedding_api_key=embedding_api_key,
            embedding_url=embedding_url,
            embedding_interface_format=embedding_interface_format,
            embedding_model_name=embedding_model_name,
            embedding_retrieval_k=embedding_retrieval_k,
            interface_format=interface_format,
            max_tokens=max_tokens,
            timeout=timeout,
            system_prompt=system_prompt,
            num_volumes=num_volumes,  # 新增：传递分卷参数
            total_chapters=total_chapters,  # 新增：传递总章节数
            gui_log_callback=gui_log_callback  # 传递回调
        )
    else:
        prompt_text = custom_prompt_text

    chapters_dir = os.path.join(filepath, "chapters")
    os.makedirs(chapters_dir, exist_ok=True)

    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )

    gui_log("   ├─ 向LLM发起请求生成草稿...")
    chapter_content = invoke_with_cleaning(llm_adapter, prompt_text, system_prompt=system_prompt)
    if not chapter_content.strip():
        gui_log("   └─ ⚠️ 生成内容为空")
        logging.warning("Generated chapter draft is empty.")
    else:
        gui_log(f"   └─ ✅ 草稿生成完成 (共{len(chapter_content)}字)\n")

    chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number}.txt")
    clear_file_content(chapter_file)
    save_string_to_txt(chapter_content, chapter_file)

    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logging.info(f"[Draft] Chapter {novel_number} generated as a draft.")

    # [Plan C] 批评家-作家 双循环优化
    # 优先使用 PromptManager 配置；如果配置加载失败则默认禁用（避免意外增加成本）
    pm = None
    try:
        pm = PromptManager()
        enable_refine = pm.is_module_enabled("chapter", "refine")
        enable_critique = pm.is_module_enabled("chapter", "critique")
    except Exception as e:
        logging.warning(f"PromptManager init failed in refine loop, fallback to disabled: {e}")
        enable_refine = False
        enable_critique = False

    # 完整的条件分支处理
    if enable_critique and enable_refine:
        gui_log("\n📚 [Plan C] 启动「批评家-作家」优化循环...")

        try:
            directory_file = os.path.join(filepath, "Novel_directory.txt")
            blueprint_text = read_file(directory_file) if os.path.exists(directory_file) else ""
            chap_info = get_chapter_info_from_blueprint(blueprint_text, novel_number) if blueprint_text else {}
            chap_title = chap_info.get("chapter_title", "")

            # 读取 Plan C 上下文（前文提要 + 上一章结尾）
            context_short_summary = ""
            context_prev_excerpt = ""

            if novel_number > 1:
                context_cache_file = os.path.join(chapters_dir, f"chapter_{novel_number}_context.json")
                cache_is_fresh = False
                if os.path.exists(context_cache_file):
                    try:
                        cache_mtime = os.path.getmtime(context_cache_file)
                        prev_chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number - 1}.txt")
                        global_summary_file = os.path.join(filepath, "global_summary.txt")

                        cache_is_fresh = True
                        if os.path.exists(prev_chapter_file):
                            if os.path.getmtime(prev_chapter_file) > cache_mtime:
                                cache_is_fresh = False
                        if os.path.exists(global_summary_file):
                            if os.path.getmtime(global_summary_file) > cache_mtime:
                                cache_is_fresh = False

                        if cache_is_fresh:
                            with open(context_cache_file, "r", encoding="utf-8") as f:
                                context_cache = json.load(f)
                            context_short_summary = context_cache.get("short_summary", "").strip()
                            context_prev_excerpt = context_cache.get("previous_chapter_excerpt", "").strip()
                        else:
                            logging.info("Plan C context cache is stale, fallback to latest files")
                    except Exception as e:
                        logging.warning(f"Failed to read Plan C context cache: {e}")

                # 若缓存缺失，尝试从章节文件回退
                if not context_prev_excerpt or not cache_is_fresh:
                    recent_texts = get_last_n_chapters_text(chapters_dir, novel_number, n=2)
                    for text in reversed(recent_texts):
                        if text.strip():
                            context_prev_excerpt = text[-800:] if len(text) > 800 else text
                            break

                # 若摘要缺失，尝试使用全局摘要兜底
                if not context_short_summary or not cache_is_fresh:
                    global_summary_file = os.path.join(filepath, "global_summary.txt")
                    context_short_summary = read_file(global_summary_file).strip()

            if not context_short_summary:
                context_short_summary = "（暂无前文摘要）"
            if not context_prev_excerpt:
                context_prev_excerpt = "（暂无上一章内容）"

            gui_log("   ├─ 批评家正在审阅初稿...")
            critique_template = pm.get_prompt("chapter", "critique") if pm else ""
            if not critique_template:
                critique_template = chapter_critique_prompt

            try:
                critique_prompt_text = critique_template.format(
                    novel_number=novel_number,
                    chapter_title=chap_title,
                    chapter_text=chapter_content,
                    short_summary=context_short_summary,
                    previous_chapter_excerpt=context_prev_excerpt
                )
            except KeyError as e:
                logging.warning(f"Critique prompt missing placeholder {e}, falling back without context")
                critique_prompt_text = critique_template.format(
                    novel_number=novel_number,
                    chapter_title=chap_title,
                    chapter_text=chapter_content
                )

            critique_response = invoke_with_cleaning(llm_adapter, critique_prompt_text, system_prompt=system_prompt)
            gui_log(f"   ├─ 收到修改意见 ({len(critique_response)}字)")
            logging.info(f"Critique received: {critique_response[:100]}...")

            gui_log("   ├─ 作家正在根据意见重写...")
            refine_template = pm.get_prompt("chapter", "refine") if pm else ""
            if not refine_template:
                refine_template = chapter_refine_prompt

            try:
                refine_prompt_text = refine_template.format(
                    critique=critique_response,
                    draft_text=chapter_content,
                    word_number=word_number,
                    short_summary=context_short_summary,
                    previous_chapter_excerpt=context_prev_excerpt
                )
            except KeyError as e:
                logging.warning(f"Refine prompt missing placeholder {e}, falling back without context")
                refine_prompt_text = refine_template.format(
                    critique=critique_response,
                    draft_text=chapter_content,
                    word_number=word_number
                )

            refined_content = invoke_with_cleaning(llm_adapter, refine_prompt_text, system_prompt=system_prompt)

            # 增强有效性校验
            is_valid = _is_valid_refined_content(refined_content, len(chapter_content))

            if is_valid:
                chapter_content = refined_content

                clear_file_content(chapter_file)
                save_string_to_txt(chapter_content, chapter_file)

                # 保存优化记录（可选，方便调试）
                debug_file = os.path.join(chapters_dir, f"chapter_{novel_number}_critique.txt")
                save_string_to_txt(
                    f"Critique:\n{critique_response}\n\nRefined:\n{refined_content}",
                    debug_file
                )

                gui_log("   └─ ✅ 优化完成，已替换初稿")
            else:
                gui_log("   └─ ⚠️ 重写内容无效，保留初稿")
                logging.warning(f"Refined content invalid: length={len(refined_content) if refined_content else 0}")

        except Exception as e:
            gui_log(f"   └─ ❌ 优化循环异常: {str(e)}")
            logging.error(f"Refine loop error: {e}")

    elif enable_critique and not enable_refine:
        gui_log("▷ [Plan C] 仅启用批评家，跳过重写（需同时启用 refine 模块）\n")
    elif not enable_critique and enable_refine:
        gui_log("▷ [Plan C] 作家模块依赖批评家，跳过重写（需同时启用 critique 模块）\n")
    else:
        # 两个都禁用，静默跳过（不输出日志，避免干扰）
        logging.debug("[Plan C] Both critique and refine disabled, skipping optimization loop")

    return chapter_content


def _is_valid_refined_content(content: str, draft_length: int) -> bool:
    """
    [Plan C] 校验重写内容是否有效

    检查规则：
    1. 内容不能为空或过短（<500字）
    2. 不能是 LLM 的拒绝响应
    3. 不能比初稿缩水太多（<40%）
    """
    if not content:
        return False

    content_length = len(content)

    # 长度过短
    if content_length < 500:
        logging.debug(f"Refined content too short: {content_length}")
        return False

    # 检查是否是 LLM 拒绝响应的常见模式
    refusal_patterns = [
        "抱歉", "无法", "不能", "对不起", "很遗憾",
        "I cannot", "I'm sorry", "I apologize", "unable to"
    ]
    first_100_chars = content[:100]
    for pattern in refusal_patterns:
        if pattern in first_100_chars:
            logging.debug(f"Refined content appears to be a refusal: found '{pattern}'")
            return False

    # 比初稿缩水太多（低于40%）
    if draft_length > 0 and content_length < draft_length * 0.4:
        logging.debug(f"Refined content too short compared to draft: {content_length} vs {draft_length}")
        return False

    return True









