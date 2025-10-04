# utils.py
# -*- coding: utf-8 -*-
import os
import json
import logging
from pathlib import Path

LOG_FILE_PATH = Path(__file__).resolve().parents[2] / "logs" / "app.log"


def get_log_file_path() -> str:
    """返回日志文件路径，若目录不存在则创建。"""
    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return str(LOG_FILE_PATH)


def read_file(filename: str) -> str:
    """读取文件的全部内容，若文件不存在或异常则返回空字符串。"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        return ""
    except Exception as e:
        print(f"[read_file] 读取文件时发生错误: {e}")
        return ""

def append_text_to_file(text_to_append: str, file_path: str):
    """在文件末尾追加文本(带换行)。若文本非空且无换行，则自动加换行。"""
    if text_to_append and not text_to_append.startswith('\n'):
        text_to_append = '\n' + text_to_append

    try:
        with open(file_path, 'a', encoding='utf-8') as file:
            file.write(text_to_append)
    except IOError as e:
        print(f"[append_text_to_file] 发生错误：{e}")

def clear_file_content(filename: str):
    """清空指定文件内容。"""
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            pass
    except IOError as e:
        print(f"[clear_file_content] 无法清空文件 '{filename}' 的内容：{e}")

def save_string_to_txt(content: str, filename: str):
    """将字符串保存为 txt 文件（覆盖写）。"""
    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)
    except Exception as e:
        print(f"[save_string_to_txt] 保存文件时发生错误: {e}")

def save_data_to_json(data: dict, file_path: str) -> bool:
    """将数据保存到 JSON 文件。"""
    try:
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"[save_data_to_json] 保存数据到JSON文件时出错: {e}")
        return False


def read_character_dynamics(filepath: str) -> str:
    """
    读取 character_dynamics.txt 文件

    Args:
        filepath: 项目路径

    Returns:
        角色动力学文本，若文件不存在则返回空字符串
    """
    char_dynamics_file = os.path.join(filepath, "character_dynamics.txt")

    if not os.path.exists(char_dynamics_file):
        logging.warning("character_dynamics.txt 不存在，可能是旧项目或角色模块被禁用")
        return ""

    content = read_file(char_dynamics_file)
    if not content:
        logging.warning("character_dynamics.txt 为空")
        return ""

    logging.info(f"成功读取角色动力学，长度：{len(content)} 字符")
    return content


def get_context_summary_for_character(
    filepath: str,
    chapter_num: int,
    num_volumes: int,
    total_chapters: int
) -> str:
    """
    获取用于角色状态更新的上下文摘要（分卷兼容）

    逻辑：
    - 非分卷模式（num_volumes <= 1）：返回 global_summary.txt
    - 第一卷：返回 global_summary.txt（本卷累积）
    - 第二卷及以后：返回 volume_{N-1}_summary.txt + global_summary.txt

    Args:
        filepath: 项目路径
        chapter_num: 当前章节号
        num_volumes: 分卷数量（0或1表示不分卷）
        total_chapters: 总章节数

    Returns:
        格式化的上下文摘要文本
    """
    global_summary_file = os.path.join(filepath, "global_summary.txt")
    global_summary = read_file(global_summary_file) if os.path.exists(global_summary_file) else ""

    # 非分卷模式
    if num_volumes <= 1:
        logging.info("非分卷模式：仅使用 global_summary.txt")
        return global_summary

    # ⚠️ 参数校验：防止 total_chapters 未配置或异常
    if total_chapters <= 0:
        logging.warning(f"分卷模式下 total_chapters={total_chapters} 无效，回退为仅使用 global_summary")
        return global_summary

    # 分卷模式：判断当前卷号
    from core.utils.volume_utils import calculate_volume_ranges, get_volume_number

    volume_ranges = calculate_volume_ranges(total_chapters, num_volumes)
    current_volume = get_volume_number(chapter_num, volume_ranges)

    if current_volume == 1:
        # 第一卷：仅全局摘要
        logging.info("第一卷：仅使用 global_summary.txt")
        return global_summary
    else:
        # 第二卷及以后：上一卷摘要 + 本卷累积摘要
        prev_volume = current_volume - 1
        prev_volume_summary_file = os.path.join(
            filepath,
            f"volume_{prev_volume}_summary.txt"
        )

        prev_volume_summary = ""
        if os.path.exists(prev_volume_summary_file):
            prev_volume_summary = read_file(prev_volume_summary_file)
            logging.info(f"读取上一卷摘要：volume_{prev_volume}_summary.txt")
        else:
            logging.warning(f"上一卷摘要不存在：volume_{prev_volume}_summary.txt")

        # 格式化组合摘要
        combined = f"""【上一卷完整摘要】
{prev_volume_summary if prev_volume_summary else '（上一卷摘要缺失）'}

【本卷累积摘要】
{global_summary if global_summary else '（本卷摘要为空）'}"""

        logging.info(f"分卷模式：第{current_volume}卷，传递上一卷+本卷摘要")
        return combined


