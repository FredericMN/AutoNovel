# ui/setting_tab_ios.py
# -*- coding: utf-8 -*-
"""
小说架构页签 - iOS风格优化版本
这是一个示例文件，展示如何使用ios_theme_helper快速改造页签
"""
import os
import customtkinter as ctk
from tkinter import messagebox
from utils import read_file, save_string_to_txt, clear_file_content
from ui.context_menu import TextWidgetContextMenu
from ui.ios_theme_helper import build_standard_edit_tab

def build_setting_tab_ios(self):
    """使用iOS风格构建小说架构页签"""
    self.setting_tab = self.tabview.add("小说架构")

    # 使用预设模板快速构建
    widgets = build_standard_edit_tab(
        parent_tab=self.setting_tab,
        title="Novel_architecture.txt",
        load_callback=self.load_novel_architecture,
        save_callback=self.save_novel_architecture
    )

    # 保存控件引用（保持与原代码兼容）
    self.setting_text = widgets["textbox"]
    self.setting_word_count_label = widgets["word_count_label"]

    # 添加右键菜单
    TextWidgetContextMenu(self.setting_text)


def load_novel_architecture(self):
    """加载小说架构文件"""
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先设置保存文件路径")
        return
    filename = os.path.join(filepath, "Novel_architecture.txt")
    content = read_file(filename)
    self.setting_text.delete("0.0", "end")
    self.setting_text.insert("0.0", content)
    self.log("已加载 Novel_architecture.txt 内容到编辑区。")


def save_novel_architecture(self):
    """保存小说架构文件"""
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先设置保存文件路径。")
        return
    content = self.setting_text.get("0.0", "end").strip()
    filename = os.path.join(filepath, "Novel_architecture.txt")
    clear_file_content(filename)
    save_string_to_txt(content, filename)
    self.log("已保存对 Novel_architecture.txt 的修改。")