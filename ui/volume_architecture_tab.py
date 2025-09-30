# ui/volume_architecture_tab.py
# -*- coding: utf-8 -*-
import os
import customtkinter as ctk
from tkinter import messagebox
from utils import read_file, save_string_to_txt, clear_file_content
from ui.context_menu import TextWidgetContextMenu

def build_volume_architecture_tab(self):
    self.volume_architecture_tab = self.tabview.add("分卷架构")
    self.volume_architecture_tab.rowconfigure(0, weight=0)
    self.volume_architecture_tab.rowconfigure(1, weight=1)
    self.volume_architecture_tab.columnconfigure(0, weight=1)

    load_btn = ctk.CTkButton(self.volume_architecture_tab, text="加载 Volume_architecture.txt", command=self.load_volume_architecture, font=("Microsoft YaHei", 12))
    load_btn.grid(row=0, column=0, padx=5, pady=5, sticky="w")

    self.volume_architecture_word_count_label = ctk.CTkLabel(self.volume_architecture_tab, text="字数：0", font=("Microsoft YaHei", 12))
    self.volume_architecture_word_count_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    save_btn = ctk.CTkButton(self.volume_architecture_tab, text="保存修改", command=self.save_volume_architecture, font=("Microsoft YaHei", 12))
    save_btn.grid(row=0, column=2, padx=5, pady=5, sticky="e")

    self.volume_architecture_text = ctk.CTkTextbox(self.volume_architecture_tab, wrap="word", font=("Microsoft YaHei", 12))
    TextWidgetContextMenu(self.volume_architecture_text)
    self.volume_architecture_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5, columnspan=3)

    def update_word_count(event=None):
        text = self.volume_architecture_text.get("0.0", "end")
        count = len(text) - 1
        self.volume_architecture_word_count_label.configure(text=f"字数：{count}")

    self.volume_architecture_text.bind("<KeyRelease>", update_word_count)
    self.volume_architecture_text.bind("<ButtonRelease>", update_word_count)

def load_volume_architecture(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先设置保存文件路径")
        return
    filename = os.path.join(filepath, "Volume_architecture.txt")
    content = read_file(filename)
    self.volume_architecture_text.delete("0.0", "end")
    self.volume_architecture_text.insert("0.0", content)
    self.log("已加载 Volume_architecture.txt 内容到编辑区。")

def save_volume_architecture(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先设置保存文件路径。")
        return
    content = self.volume_architecture_text.get("0.0", "end").strip()
    filename = os.path.join(filepath, "Volume_architecture.txt")
    clear_file_content(filename)
    save_string_to_txt(content, filename)
    self.log("已保存对 Volume_architecture.txt 的修改。")