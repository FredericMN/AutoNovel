# ui/volume_summary_tab.py
# -*- coding: utf-8 -*-
import os
import glob
import customtkinter as ctk
from tkinter import messagebox
from utils import read_file, save_string_to_txt, clear_file_content
from ui.context_menu import TextWidgetContextMenu

def build_volume_summary_tab(self):
    self.volume_summary_tab = self.tabview.add("分卷概要")
    self.volume_summary_tab.rowconfigure(0, weight=0)
    self.volume_summary_tab.rowconfigure(1, weight=0)
    self.volume_summary_tab.rowconfigure(2, weight=1)
    self.volume_summary_tab.columnconfigure(0, weight=1)

    # 顶部操作按钮区域
    top_frame = ctk.CTkFrame(self.volume_summary_tab, fg_color="transparent")
    top_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
    top_frame.columnconfigure(0, weight=0)
    top_frame.columnconfigure(1, weight=1)
    top_frame.columnconfigure(2, weight=0)

    refresh_btn = ctk.CTkButton(top_frame, text="刷新分卷列表", command=self.refresh_volume_list, font=("Microsoft YaHei", 12), width=120)
    refresh_btn.grid(row=0, column=0, padx=5, pady=0, sticky="w")

    self.volume_summary_word_count_label = ctk.CTkLabel(top_frame, text="字数：0", font=("Microsoft YaHei", 12))
    self.volume_summary_word_count_label.grid(row=0, column=1, padx=5, pady=0, sticky="w")

    save_btn = ctk.CTkButton(top_frame, text="保存修改", command=self.save_volume_summary, font=("Microsoft YaHei", 12), width=100)
    save_btn.grid(row=0, column=2, padx=5, pady=0, sticky="e")

    # 分卷选择区域（使用 Segmented Button）
    volume_selector_frame = ctk.CTkFrame(self.volume_summary_tab, fg_color="transparent")
    volume_selector_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)

    selector_label = ctk.CTkLabel(volume_selector_frame, text="选择分卷：", font=("Microsoft YaHei", 12))
    selector_label.pack(side="left", padx=(5, 10))

    # 初始化分卷选择器（动态生成）
    self.volume_selector = None
    self.current_volume_number = 1  # 当前选中的分卷编号
    self.volume_files_list = []  # 存储检测到的分卷文件列表

    # 文本编辑区域
    self.volume_summary_text = ctk.CTkTextbox(self.volume_summary_tab, wrap="word", font=("Microsoft YaHei", 12))
    TextWidgetContextMenu(self.volume_summary_text)
    self.volume_summary_text.grid(row=2, column=0, sticky="nsew", padx=5, pady=5)

    def update_word_count(event=None):
        text = self.volume_summary_text.get("0.0", "end")
        count = len(text) - 1
        self.volume_summary_word_count_label.configure(text=f"字数：{count}")

    self.volume_summary_text.bind("<KeyRelease>", update_word_count)
    self.volume_summary_text.bind("<ButtonRelease>", update_word_count)

    # 初始化时自动刷新分卷列表
    self.master.after(100, self.refresh_volume_list)

def refresh_volume_list(self):
    """刷新分卷文件列表并更新选择器"""
    filepath = self.filepath_var.get().strip()
    if not filepath:
        self.log("⚠ 请先设置保存文件路径")
        return

    # 查找所有 volume_X_summary.txt 文件
    pattern = os.path.join(filepath, "volume_*_summary.txt")
    volume_files = sorted(glob.glob(pattern))

    # 提取分卷编号
    self.volume_files_list = []
    for file_path in volume_files:
        filename = os.path.basename(file_path)
        # 解析 volume_X_summary.txt 中的 X
        try:
            volume_num = int(filename.split('_')[1])
            self.volume_files_list.append(volume_num)
        except (IndexError, ValueError):
            continue

    if not self.volume_files_list:
        self.log("⚠ 未检测到分卷概要文件（volume_X_summary.txt）")
        # 清空选择器
        if hasattr(self, 'volume_selector') and self.volume_selector:
            self.volume_selector.destroy()
            self.volume_selector = None
        self.volume_summary_text.delete("0.0", "end")
        self.volume_summary_text.insert("0.0", "未检测到分卷概要文件\n\n提示：请先运行分卷生成流程")
        return

    # 创建/更新选择器
    volume_selector_frame = self.volume_summary_tab.grid_slaves(row=1, column=0)[0]

    # 销毁旧选择器
    if hasattr(self, 'volume_selector') and self.volume_selector:
        self.volume_selector.destroy()

    # 生成按钮标签
    volume_labels = [f"第{vol}卷" for vol in self.volume_files_list]

    # 创建新选择器
    self.volume_selector = ctk.CTkSegmentedButton(
        volume_selector_frame,
        values=volume_labels,
        command=self.on_volume_selected,
        font=("Microsoft YaHei", 12)
    )
    self.volume_selector.pack(side="left", fill="x", expand=True, padx=5)

    # 默认选择第一个分卷
    if self.volume_files_list:
        self.current_volume_number = self.volume_files_list[0]
        self.volume_selector.set(f"第{self.current_volume_number}卷")
        self.load_volume_summary(self.current_volume_number)

    self.log(f"✅ 检测到 {len(self.volume_files_list)} 个分卷概要文件")

def on_volume_selected(self, selected_label):
    """分卷选择器回调函数"""
    # 解析选中的分卷编号（从"第X卷"中提取X）
    try:
        volume_num = int(selected_label.replace("第", "").replace("卷", ""))
        self.current_volume_number = volume_num
        self.load_volume_summary(volume_num)
    except ValueError:
        self.log(f"⚠ 解析分卷编号失败：{selected_label}")

def load_volume_summary(self, volume_number=None):
    """加载指定分卷的概要文件"""
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先设置保存文件路径")
        return

    if volume_number is None:
        volume_number = self.current_volume_number

    filename = os.path.join(filepath, f"volume_{volume_number}_summary.txt")
    content = read_file(filename)

    if content.strip():
        self.volume_summary_text.delete("0.0", "end")
        self.volume_summary_text.insert("0.0", content)
        self.log(f"已加载 volume_{volume_number}_summary.txt 内容到编辑区。")
    else:
        self.volume_summary_text.delete("0.0", "end")
        self.volume_summary_text.insert("0.0", f"文件不存在或为空：volume_{volume_number}_summary.txt")

def save_volume_summary(self):
    """保存当前分卷的概要文件"""
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先设置保存文件路径")
        return

    if not hasattr(self, 'current_volume_number'):
        messagebox.showwarning("警告", "请先选择要保存的分卷")
        return

    content = self.volume_summary_text.get("0.0", "end").strip()
    filename = os.path.join(filepath, f"volume_{self.current_volume_number}_summary.txt")
    clear_file_content(filename)
    save_string_to_txt(content, filename)
    self.log(f"已保存对 volume_{self.current_volume_number}_summary.txt 的修改。")