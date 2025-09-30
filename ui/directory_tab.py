# ui/directory_tab.py
# -*- coding: utf-8 -*-
import os
import customtkinter as ctk
from tkinter import messagebox
from utils import read_file, save_string_to_txt, clear_file_content
from ui.context_menu import TextWidgetContextMenu
from ui.ios_theme import IOSColors, IOSLayout, IOSStyles

def build_directory_tab(self):
    self.directory_tab = self.tabview.add("目录蓝图")
    self.directory_tab.configure(fg_color=IOSColors.BG_CARD)
    self.directory_tab.rowconfigure(0, weight=0)
    self.directory_tab.rowconfigure(1, weight=1)
    self.directory_tab.columnconfigure(0, weight=1)

    # 按钮工具栏
    toolbar_frame = ctk.CTkFrame(self.directory_tab, fg_color="transparent")
    toolbar_frame.grid(row=0, column=0, sticky="ew", padx=IOSLayout.PADDING_LARGE, pady=IOSLayout.PADDING_LARGE)
    toolbar_frame.columnconfigure(1, weight=1)

    # 应用iOS按钮样式
    btn_style = IOSStyles.primary_button()
    load_btn = ctk.CTkButton(toolbar_frame, text="加载 Novel_directory.txt", command=self.load_chapter_blueprint, **btn_style)
    load_btn.grid(row=0, column=0, padx=(0, IOSLayout.PADDING_SMALL), sticky="w")

    label_style = IOSStyles.label_normal()
    self.directory_word_count_label = ctk.CTkLabel(toolbar_frame, text="字数：0", **label_style)
    self.directory_word_count_label.grid(row=0, column=1, padx=IOSLayout.PADDING_MEDIUM, sticky="w")

    save_btn = ctk.CTkButton(toolbar_frame, text="保存修改", command=self.save_chapter_blueprint, **btn_style)
    save_btn.grid(row=0, column=2, padx=0, sticky="e")

    # 应用iOS文本框样式（卡片式边框）
    textbox_style = IOSStyles.textbox()
    self.directory_text = ctk.CTkTextbox(self.directory_tab, wrap="word", **textbox_style)
    TextWidgetContextMenu(self.directory_text)
    self.directory_text.grid(row=1, column=0, sticky="nsew", padx=IOSLayout.PADDING_LARGE, pady=(0, IOSLayout.PADDING_LARGE))

    def update_word_count(event=None):
        text = self.directory_text.get("0.0", "end")
        count = len(text) - 1
        self.directory_word_count_label.configure(text=f"字数：{count}")

    self.directory_text.bind("<KeyRelease>", update_word_count)
    self.directory_text.bind("<ButtonRelease>", update_word_count)

def load_chapter_blueprint(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先设置保存文件路径")
        return
    filename = os.path.join(filepath, "Novel_directory.txt")
    content = read_file(filename)
    self.directory_text.delete("0.0", "end")
    self.directory_text.insert("0.0", content)
    self.log("已加载 Novel_directory.txt 内容到编辑区。")

def save_chapter_blueprint(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先设置保存文件路径")
        return
    content = self.directory_text.get("0.0", "end").strip()
    filename = os.path.join(filepath, "Novel_directory.txt")
    clear_file_content(filename)
    save_string_to_txt(content, filename)
    self.log("已保存对 Novel_directory.txt 的修改。")
