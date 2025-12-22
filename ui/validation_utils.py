# ui/validation_utils.py
# -*- coding: utf-8 -*-
"""
防呆校验工具模块
包含章节连续性校验、配置一致性检查、保存状态指示器等功能
"""
import os
from typing import Dict, List, Optional
from datetime import datetime
import customtkinter as ctk
import tkinter as tk
from ui.ios_theme import IOSFonts


def validate_chapter_continuity(filepath: str, chapter_num: int) -> dict:
    """
    校验章节连续性

    Args:
        filepath: 小说项目路径
        chapter_num: 要生成的章节号

    Returns:
        {
            "valid": bool,           # 是否通过校验
            "error_type": str,       # 错误类型
            "message": str,          # 错误提示
            "suggestion": str,       # 建议操作
            "missing_chapters": list # 缺失的章节号列表
        }
    """
    chapters_dir = os.path.join(filepath, "chapters")

    # 检查是否存在章节目录
    if not os.path.exists(chapters_dir):
        if chapter_num != 1:
            return {
                "valid": False,
                "error_type": "no_chapters_exist",
                "message": "⚠️ 章节连续性检查失败",
                "suggestion": (
                    f"当前没有任何章节，但您设置的章节号为 {chapter_num}。\n\n"
                    f"建议先生成第1章。"
                ),
                "missing_chapters": list(range(1, chapter_num))
            }
        return {"valid": True}

    # 检查已生成的章节
    existing_chapters = []
    for i in range(1, chapter_num):
        chapter_file = os.path.join(chapters_dir, f"chapter_{i}.txt")
        if os.path.exists(chapter_file):
            existing_chapters.append(i)

    # 查找缺失章节
    missing_chapters = []
    for i in range(1, chapter_num):
        if i not in existing_chapters:
            missing_chapters.append(i)

    if missing_chapters:
        # 格式化缺失章节列表
        if len(missing_chapters) <= 5:
            missing_str = ", ".join(map(str, missing_chapters))
        else:
            missing_str = ", ".join(map(str, missing_chapters[:5])) + f" ... 等共{len(missing_chapters)}章"

        return {
            "valid": False,
            "error_type": "missing_chapters",
            "message": "⚠️ 检测到章节缺失",
            "suggestion": (
                f"当前要生成：第 {chapter_num} 章\n"
                f"已生成章节：{', '.join(map(str, existing_chapters)) if existing_chapters else '无'}\n"
                f"缺失章节：{missing_str}\n\n"
                f"建议操作：\n"
                f"1. 先生成第 {missing_chapters[0]} 章\n"
                f"2. 或者修改章节号为 {len(existing_chapters) + 1}"
            ),
            "missing_chapters": missing_chapters
        }

    return {"valid": True}


def check_critical_files_exist(filepath: str) -> dict:
    """
    检查关键文件是否存在

    Args:
        filepath: 小说项目路径

    Returns:
        {
            "architecture_exists": bool,          # 架构文件是否存在
            "directory_exists": bool,             # 目录文件是否存在
            "volume_architecture_exists": bool,   # 分卷架构是否存在
            "any_chapter_exists": bool,           # 是否有任何章节存在
            "is_locked": bool                     # 是否应锁定配置
        }
    """
    result = {
        "architecture_exists": os.path.exists(os.path.join(filepath, "Novel_architecture.txt")),
        "directory_exists": os.path.exists(os.path.join(filepath, "Novel_directory.txt")),
        "volume_architecture_exists": os.path.exists(os.path.join(filepath, "Volume_architecture.txt")),
        "any_chapter_exists": False
    }

    # 检查是否有任何章节生成
    chapters_dir = os.path.join(filepath, "chapters")
    if os.path.exists(chapters_dir):
        for f in os.listdir(chapters_dir):
            if f.startswith("chapter_") and f.endswith(".txt"):
                result["any_chapter_exists"] = True
                break

    # 判断是否应锁定（只要目录存在就锁定，因为目录包含章节数和分卷信息）
    result["is_locked"] = result["directory_exists"] or result["any_chapter_exists"]

    return result


def validate_config_changes(old_config: dict, new_config: dict, filepath: str) -> dict:
    """
    检测关键配置变更

    Args:
        old_config: 旧配置
        new_config: 新配置
        filepath: 小说项目路径

    Returns:
        {
            "has_critical_changes": bool,  # 是否有关键变更
            "changes": list,               # 变更项列表
            "warnings": list               # 警告信息
        }
    """
    result = {
        "has_critical_changes": False,
        "changes": [],
        "warnings": []
    }

    # 检查章节数变更
    old_chapters = old_config.get("other_params", {}).get("num_chapters", 0)
    new_chapters = new_config.get("other_params", {}).get("num_chapters", 0)

    if old_chapters != new_chapters:
        result["has_critical_changes"] = True
        result["changes"].append(f"章节数: {old_chapters} → {new_chapters}")

        # 检查是否已有目录
        if os.path.exists(os.path.join(filepath, "Novel_directory.txt")):
            result["warnings"].append(
                "⚠️ 已存在章节目录文件，修改章节数可能导致目录与实际不符。\n"
                "   建议删除 Novel_directory.txt 并重新生成。"
            )

    # 检查分卷数变更
    old_volumes = old_config.get("other_params", {}).get("num_volumes", 0)
    new_volumes = new_config.get("other_params", {}).get("num_volumes", 0)

    if old_volumes != new_volumes:
        result["has_critical_changes"] = True
        result["changes"].append(f"分卷数: {old_volumes} → {new_volumes}")

        # 检查是否已有分卷架构
        if os.path.exists(os.path.join(filepath, "Volume_architecture.txt")):
            result["warnings"].append(
                "⚠️ 已存在分卷架构文件，修改分卷数会导致卷号计算错误。\n"
                "   建议删除 Volume_architecture.txt 并重新生成。"
            )

    return result


def auto_detect_next_chapter(filepath: str) -> int:
    """
    自动检测下一个应该生成的章节号

    Args:
        filepath: 小说项目路径

    Returns:
        下一个应生成的章节号
    """
    chapters_dir = os.path.join(filepath, "chapters")
    if not os.path.exists(chapters_dir):
        return 1

    # 找到最大的连续章节号
    chapter_num = 1
    while True:
        chapter_file = os.path.join(chapters_dir, f"chapter_{chapter_num}.txt")
        if not os.path.exists(chapter_file):
            break
        chapter_num += 1

    return chapter_num


class SaveStatusIndicator:
    """保存状态指示器组件 - iOS风格（仅文字版本）"""

    def __init__(self, parent_frame):
        """
        初始化保存状态指示器

        Args:
            parent_frame: 父容器（通常是 ScrollableFrame 的标签栏）
        """
        self.frame = ctk.CTkFrame(parent_frame, fg_color="transparent")

        # 状态文字（移除圆点图标，只保留文字）
        self.status_text = ctk.CTkLabel(
            self.frame,
            text="已保存",
            font=IOSFonts.get_font(11),
            text_color="#00AA00"
        )
        self.status_text.grid(row=0, column=0, padx=3)

        # 最后保存时间
        self.time_label = ctk.CTkLabel(
            self.frame,
            text="",
            font=IOSFonts.get_font(10),
            text_color="gray"
        )
        self.time_label.grid(row=0, column=1, padx=5)

    def set_saved(self):
        """设置为已保存状态"""
        self.status_text.configure(
            text="已保存",
            text_color="#00AA00"
        )
        current_time = datetime.now().strftime('%H:%M:%S')
        self.time_label.configure(text=f"保存于 {current_time}")

    def set_unsaved(self):
        """设置为未保存状态"""
        self.status_text.configure(
            text="尚未保存",
            text_color="#FF3B30"
        )
        self.time_label.configure(text="有未保存的修改")

    def set_saving(self):
        """设置为保存中状态"""
        self.status_text.configure(
            text="保存中...",
            text_color="#FF9500"
        )
        self.time_label.configure(text="")

    def pack(self, **kwargs):
        """将指示器放置到父容器中"""
        self.frame.pack(**kwargs)

    def grid(self, **kwargs):
        """使用grid布局放置指示器"""
        self.frame.grid(**kwargs)
