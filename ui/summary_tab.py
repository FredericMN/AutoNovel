# ui/summary_tab.py
# -*- coding: utf-8 -*-
import os
import customtkinter as ctk
from tkinter import messagebox
from utils import read_file, save_string_to_txt, clear_file_content
from ui.context_menu import TextWidgetContextMenu
from ui.ios_theme import IOSColors, IOSLayout, IOSStyles

def build_summary_tab(self):
    self.summary_tab = self.tabview.add("全局概要")
    self.summary_tab.configure(fg_color=IOSColors.BG_CARD)
    self.summary_tab.rowconfigure(0, weight=0)
    self.summary_tab.rowconfigure(1, weight=1)
    self.summary_tab.columnconfigure(0, weight=1)

    # 按钮工具栏
    toolbar_frame = ctk.CTkFrame(self.summary_tab, fg_color="transparent")
    toolbar_frame.grid(row=0, column=0, sticky="ew", padx=IOSLayout.PADDING_LARGE, pady=IOSLayout.PADDING_LARGE)
    toolbar_frame.columnconfigure(1, weight=1)

    # 应用iOS按钮样式
    btn_style = IOSStyles.primary_button()
    load_btn = ctk.CTkButton(toolbar_frame, text="加载 global_summary.txt", command=self.load_global_summary, **btn_style)
    load_btn.grid(row=0, column=0, padx=(0, IOSLayout.PADDING_SMALL), sticky="w")

    label_style = IOSStyles.label_normal()
    self.word_count_label = ctk.CTkLabel(toolbar_frame, text="字数：0", **label_style)
    self.word_count_label.grid(row=0, column=1, padx=IOSLayout.PADDING_MEDIUM, sticky="w")

    save_btn = ctk.CTkButton(toolbar_frame, text="保存修改", command=self.save_global_summary, **btn_style)
    save_btn.grid(row=0, column=2, padx=0, sticky="e")

    # 应用iOS文本框样式（卡片式边框）
    textbox_style = IOSStyles.textbox()
    self.summary_text = ctk.CTkTextbox(self.summary_tab, wrap="word", **textbox_style)
    TextWidgetContextMenu(self.summary_text)
    self.summary_text.grid(row=1, column=0, sticky="nsew", padx=IOSLayout.PADDING_LARGE, pady=(0, IOSLayout.PADDING_LARGE))

    def update_word_count(event=None):
        text = self.summary_text.get("0.0", "end")
        count = len(text) - 1
        self.word_count_label.configure(text=f"字数：{count}")

    self.summary_text.bind("<KeyRelease>", update_word_count)
    self.summary_text.bind("<ButtonRelease>", update_word_count)
def load_global_summary(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先设置保存文件路径")
        return
    filename = os.path.join(filepath, "global_summary.txt")
    content = read_file(filename)
    self.summary_text.delete("0.0", "end")
    self.summary_text.insert("0.0", content)
    self.log("已加载 global_summary.txt 到编辑区。")

def save_global_summary(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先设置保存文件路径")
        return
    content = self.summary_text.get("0.0", "end").strip()
    filename = os.path.join(filepath, "global_summary.txt")
    clear_file_content(filename)
    save_string_to_txt(content, filename)
    self.log("已保存对 global_summary.txt 的修改。")
