# ui/chapters_tab.py
# -*- coding: utf-8 -*-
import os
import customtkinter as ctk
from tkinter import messagebox
from ui.context_menu import TextWidgetContextMenu
from core.utils.file_utils import read_file, save_string_to_txt, clear_file_content
from core.utils.chapter_directory_parser import get_chapter_info_from_blueprint
from ui.ios_theme import IOSColors, IOSLayout, IOSFonts

def build_chapters_tab(self):
    self.chapters_view_tab = self.tabview.add("章节管理")
    self.chapters_view_tab.rowconfigure(0, weight=0)  # 工具栏
    self.chapters_view_tab.rowconfigure(1, weight=0)  # 信息展示行
    self.chapters_view_tab.rowconfigure(2, weight=1)  # 文本编辑区
    self.chapters_view_tab.columnconfigure(0, weight=1)

    top_frame = ctk.CTkFrame(self.chapters_view_tab)
    top_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
    top_frame.columnconfigure(0, weight=0)
    top_frame.columnconfigure(1, weight=0)
    top_frame.columnconfigure(2, weight=0)
    top_frame.columnconfigure(3, weight=0)
    top_frame.columnconfigure(4, weight=1)

    prev_btn = ctk.CTkButton(top_frame, text="<< 上一章", command=self.prev_chapter, font=IOSFonts.get_font(12))
    prev_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")

    next_btn = ctk.CTkButton(top_frame, text="下一章 >>", command=self.next_chapter, font=IOSFonts.get_font(12))
    next_btn.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    self.chapter_select_var = ctk.StringVar(value="")
    self.chapter_select_menu = ctk.CTkOptionMenu(top_frame, values=[], variable=self.chapter_select_var, command=self.on_chapter_selected, font=IOSFonts.get_font(12))
    self.chapter_select_menu.grid(row=0, column=2, padx=5, pady=5, sticky="w")

    save_btn = ctk.CTkButton(top_frame, text="保存修改", command=self.save_current_chapter, font=IOSFonts.get_font(12))
    save_btn.grid(row=0, column=3, padx=5, pady=5, sticky="w")

    refresh_btn = ctk.CTkButton(top_frame, text="刷新章节列表", command=self.refresh_chapters_list, font=IOSFonts.get_font(12))
    refresh_btn.grid(row=0, column=5, padx=5, pady=5, sticky="e")

    self.chapters_word_count_label = ctk.CTkLabel(top_frame, text="字数：0", font=IOSFonts.get_font(12))
    self.chapters_word_count_label.grid(row=0, column=4, padx=(0,10), sticky="e")

    # ========== 信息展示行 ==========
    info_frame = ctk.CTkFrame(
        self.chapters_view_tab,
        fg_color=IOSColors.BG_CARD,
        corner_radius=IOSLayout.CORNER_RADIUS_MEDIUM,
        border_width=1,
        border_color=IOSColors.SEPARATOR
    )
    info_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))

    # 使用Entry代替Label，支持文本选择和复制
    self.chapter_info_entry = ctk.CTkEntry(
        info_frame,
        font=IOSFonts.get_font(IOSLayout.FONT_SIZE_MEDIUM),
        text_color=IOSColors.TEXT_SECONDARY,
        fg_color=IOSColors.BG_CARD,
        border_width=0,
        state="readonly"  # 只读状态
    )
    self.chapter_info_entry.pack(side="left", fill="x", expand=True, padx=IOSLayout.PADDING_MEDIUM, pady=IOSLayout.PADDING_SMALL)

    # 设置初始文本
    self.chapter_info_entry.configure(state="normal")
    self.chapter_info_entry.delete(0, "end")
    self.chapter_info_entry.insert(0, "📖 暂无章节信息")
    self.chapter_info_entry.configure(state="readonly")

    self.chapter_view_text = ctk.CTkTextbox(self.chapters_view_tab, wrap="word", font=IOSFonts.get_font(15))
    
    def update_word_count(event=None):
        text = self.chapter_view_text.get("0.0", "end-1c")
        text_length = len(text)
        self.chapters_word_count_label.configure(text=f"字数：{text_length}")
    
    self.chapter_view_text.bind("<KeyRelease>", update_word_count)
    self.chapter_view_text.bind("<ButtonRelease>", update_word_count)
    TextWidgetContextMenu(self.chapter_view_text)
    self.chapter_view_text.grid(row=2, column=0, sticky="nsew", padx=5, pady=5, columnspan=6)

    self.chapters_list = []
    refresh_chapters_list(self)

def refresh_chapters_list(self):
    filepath = self.filepath_var.get().strip()
    chapters_dir = os.path.join(filepath, "chapters")
    if not os.path.exists(chapters_dir):
        self.safe_log("尚未找到 chapters 文件夹，请先生成章节或检查保存路径。")
        self.chapter_select_menu.configure(values=[])
        # 更新Entry文本
        self.chapter_info_entry.configure(state="normal")
        self.chapter_info_entry.delete(0, "end")
        self.chapter_info_entry.insert(0, "📖 暂无章节信息")
        self.chapter_info_entry.configure(state="readonly")
        return

    all_files = os.listdir(chapters_dir)
    chapter_nums = []
    for f in all_files:
        if f.startswith("chapter_") and f.endswith(".txt"):
            number_part = f.replace("chapter_", "").replace(".txt", "")
            if number_part.isdigit():
                chapter_nums.append(number_part)
    chapter_nums.sort(key=lambda x: int(x))
    self.chapters_list = chapter_nums
    self.chapter_select_menu.configure(values=self.chapters_list)
    current_selected = self.chapter_select_var.get()
    if current_selected not in self.chapters_list:
        if self.chapters_list:
            self.chapter_select_var.set(self.chapters_list[0])
            load_chapter_content(self, self.chapters_list[0])
        else:
            self.chapter_select_var.set("")
            self.chapter_view_text.delete("0.0", "end")
            # 更新Entry文本
            self.chapter_info_entry.configure(state="normal")
            self.chapter_info_entry.delete(0, "end")
            self.chapter_info_entry.insert(0, "📖 暂无章节信息")
            self.chapter_info_entry.configure(state="readonly")
    else:
        # 当前选中的章节仍然存在，更新信息显示
        update_chapter_info_display(self, current_selected)

def on_chapter_selected(self, value):
    load_chapter_content(self, value)

def load_chapter_content(self, chapter_number_str):
    if not chapter_number_str:
        return
    filepath = self.filepath_var.get().strip()
    chapter_file = os.path.join(filepath, "chapters", f"chapter_{chapter_number_str}.txt")
    if not os.path.exists(chapter_file):
        self.safe_log(f"章节文件 {chapter_file} 不存在！")
        return
    content = read_file(chapter_file)
    self.chapter_view_text.delete("0.0", "end")
    self.chapter_view_text.insert("0.0", content)
    # 更新章节信息展示
    update_chapter_info_display(self, chapter_number_str)

def save_current_chapter(self):
    chapter_number_str = self.chapter_select_var.get()
    if not chapter_number_str:
        messagebox.showwarning("警告", "尚未选择章节，无法保存。")
        return
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径")
        return
    chapter_file = os.path.join(filepath, "chapters", f"chapter_{chapter_number_str}.txt")
    content = self.chapter_view_text.get("0.0", "end").strip()
    clear_file_content(chapter_file)
    save_string_to_txt(content, chapter_file)
    self.safe_log(f"已保存对第 {chapter_number_str} 章的修改。")

def prev_chapter(self):
    if not self.chapters_list:
        return
    current = self.chapter_select_var.get()
    if current not in self.chapters_list:
        return
    idx = self.chapters_list.index(current)
    if idx > 0:
        new_idx = idx - 1
        self.chapter_select_var.set(self.chapters_list[new_idx])
        load_chapter_content(self, self.chapters_list[new_idx])
    else:
        messagebox.showinfo("提示", "已经是第一章了。")

def next_chapter(self):
    if not self.chapters_list:
        return
    current = self.chapter_select_var.get()
    if current not in self.chapters_list:
        return
    idx = self.chapters_list.index(current)
    if idx < len(self.chapters_list) - 1:
        new_idx = idx + 1
        self.chapter_select_var.set(self.chapters_list[new_idx])
        load_chapter_content(self, self.chapters_list[new_idx])
    else:
        messagebox.showinfo("提示", "已经是最后一章了。")


def update_chapter_info_display(self, chapter_number_str):
    """
    更新章节信息展示行（增强版，优化容错和显示逻辑）
    :param chapter_number_str: 章节编号（字符串）
    """
    def set_info_text(text):
        """辅助函数：更新只读Entry的文本"""
        self.chapter_info_entry.configure(state="normal")
        self.chapter_info_entry.delete(0, "end")
        self.chapter_info_entry.insert(0, text)
        self.chapter_info_entry.configure(state="readonly")

    if not chapter_number_str:
        set_info_text("📖 暂无章节信息")
        return

    try:
        chapter_num = int(chapter_number_str)
        filepath = self.filepath_var.get().strip()

        # 读取 Novel_directory.txt 文件
        directory_file = os.path.join(filepath, "Novel_directory.txt")
        if not os.path.exists(directory_file):
            set_info_text(f"📖 第{chapter_num}章")
            return

        blueprint_text = read_file(directory_file)
        if not blueprint_text:
            set_info_text(f"📖 第{chapter_num}章")
            return

        # 解析章节信息
        chapter_info = get_chapter_info_from_blueprint(blueprint_text, chapter_num)

        # 构建显示文本
        display_parts = []

        # 卷信息（如果存在）
        if chapter_info.get('volume_number') and chapter_info.get('volume_title'):
            volume_text = f"第{chapter_info['volume_number']}卷：{chapter_info['volume_title']}"
            display_parts.append(volume_text)

        # 章节信息（优化处理逻辑）
        chapter_title = chapter_info.get('chapter_title', '').strip()

        # 处理各种章节标题格式
        if chapter_title:
            # 如果标题已经包含"第X章"，直接使用
            if chapter_title.startswith(f'第{chapter_num}章'):
                chapter_text = chapter_title
            # 如果标题不包含章节号，添加上
            elif not chapter_title.startswith('第') or '章' not in chapter_title:
                chapter_text = f"第{chapter_num}章：{chapter_title}"
            else:
                chapter_text = chapter_title
        else:
            # 没有标题时，仅显示章节号
            chapter_text = f"第{chapter_num}章"

        display_parts.append(chapter_text)

        # 组合显示文本
        if len(display_parts) > 1:
            # 有卷信息和章节信息
            display_text = " | ".join(display_parts)
        elif display_parts:
            # 仅有章节信息
            display_text = display_parts[0]
        else:
            # 降级显示
            display_text = f"第{chapter_num}章"

        set_info_text(f"📖 {display_text}")

    except Exception as e:
        # 解析失败时回退显示
        try:
            chapter_num = int(chapter_number_str)
            set_info_text(f"📖 第{chapter_num}章")
        except:
            set_info_text("📖 暂无章节信息")


