# ui/main_tab.py
# -*- coding: utf-8 -*-
import customtkinter as ctk
from tkinter import messagebox
from ui.context_menu import TextWidgetContextMenu

def build_main_tab(self):
    """
    主Tab包含三段式布局：左侧本章内容、中间日志与按钮、右侧小说参数
    """
    self.main_tab = self.tabview.add("主界面")
    self.main_tab.rowconfigure(0, weight=1)

    # 配置三段列宽：每段最小300px，默认500px，权重相等
    self.main_tab.columnconfigure(0, weight=1, minsize=500)  # 左侧：本章内容
    self.main_tab.columnconfigure(1, weight=1, minsize=500)  # 中间：日志+按钮
    self.main_tab.columnconfigure(2, weight=1, minsize=500)  # 右侧：小说参数

    # 左侧：本章内容
    self.left_frame = ctk.CTkFrame(self.main_tab)
    self.left_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

    # 中间：日志+按钮+进度条
    self.center_frame = ctk.CTkFrame(self.main_tab)
    self.center_frame.grid(row=0, column=1, sticky="nsew", padx=2, pady=2)

    # 右侧：小说参数
    self.right_frame = ctk.CTkFrame(self.main_tab)
    self.right_frame.grid(row=0, column=2, sticky="nsew", padx=2, pady=2)

    build_left_layout(self)
    build_center_layout(self)
    build_right_layout(self)

def build_left_layout(self):
    """
    左侧区域：仅本章内容(可编辑)
    """
    self.left_frame.grid_rowconfigure(0, weight=0)
    self.left_frame.grid_rowconfigure(1, weight=1)
    self.left_frame.columnconfigure(0, weight=1)

    self.chapter_label = ctk.CTkLabel(self.left_frame, text="本章内容（可编辑）  字数：0", font=("Microsoft YaHei", 12))
    self.chapter_label.grid(row=0, column=0, padx=5, pady=(5, 0), sticky="w")

    # 章节文本编辑框
    self.chapter_result = ctk.CTkTextbox(self.left_frame, wrap="word", font=("Microsoft YaHei", 14))
    TextWidgetContextMenu(self.chapter_result)
    self.chapter_result.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5))

    def update_word_count(event=None):
        text = self.chapter_result.get("0.0", "end")
        count = len(text) - 1  # 减去最后一个换行符
        self.chapter_label.configure(text=f"本章内容（可编辑）  字数：{count}")

    self.chapter_result.bind("<KeyRelease>", update_word_count)
    self.chapter_result.bind("<ButtonRelease>", update_word_count)

def build_center_layout(self):
    """
    中间区域：Step按钮 + 进度条 + 输出日志
    """
    self.center_frame.grid_rowconfigure(0, weight=0)  # Step按钮
    self.center_frame.grid_rowconfigure(1, weight=0)  # 进度条
    self.center_frame.grid_rowconfigure(2, weight=0)  # 日志标签
    self.center_frame.grid_rowconfigure(3, weight=1)  # 日志内容
    self.center_frame.columnconfigure(0, weight=1)

    # Step 按钮区域（两行布局）
    self.step_buttons_frame = ctk.CTkFrame(self.center_frame)
    self.step_buttons_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
    self.step_buttons_frame.columnconfigure((0, 1, 2, 3), weight=1)

    # 第一行：1-4步骤按钮
    self.btn_generate_architecture = ctk.CTkButton(
        self.step_buttons_frame,
        text="1. 生成架构",
        command=self.generate_novel_architecture_ui,
        font=("Microsoft YaHei", 12),
        height=32
    )
    self.btn_generate_architecture.grid(row=0, column=0, padx=3, pady=3, sticky="ew")

    self.btn_generate_directory = ctk.CTkButton(
        self.step_buttons_frame,
        text="2. 生成目录",
        command=self.generate_chapter_blueprint_ui,
        font=("Microsoft YaHei", 12),
        height=32
    )
    self.btn_generate_directory.grid(row=0, column=1, padx=3, pady=3, sticky="ew")

    self.btn_generate_chapter = ctk.CTkButton(
        self.step_buttons_frame,
        text="3. 生成草稿",
        command=self.generate_chapter_draft_ui,
        font=("Microsoft YaHei", 12),
        height=32
    )
    self.btn_generate_chapter.grid(row=0, column=2, padx=3, pady=3, sticky="ew")

    self.btn_finalize_chapter = ctk.CTkButton(
        self.step_buttons_frame,
        text="4. 定稿章节",
        command=self.finalize_chapter_ui,
        font=("Microsoft YaHei", 12),
        height=32
    )
    self.btn_finalize_chapter.grid(row=0, column=3, padx=3, pady=3, sticky="ew")

    # 第二行：批量生成按钮（居中显示）
    self.btn_batch_generate = ctk.CTkButton(
        self.step_buttons_frame,
        text="批量生成",
        command=self.generate_batch_ui,
        font=("Microsoft YaHei", 12, "bold"),
        height=32,
        fg_color="#2B7A78"
    )
    self.btn_batch_generate.grid(row=1, column=1, columnspan=2, padx=3, pady=3, sticky="ew")

    # 进度条区域（默认隐藏）
    self.progress_frame = ctk.CTkFrame(self.center_frame)
    self.progress_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
    self.progress_frame.columnconfigure(0, weight=1)
    self.progress_frame.grid_remove()  # 默认隐藏

    # 整体进度标签
    self.overall_progress_label = ctk.CTkLabel(
        self.progress_frame,
        text="整体进度: 0/0 (0%)",
        font=("Microsoft YaHei", 11, "bold"),
        anchor="w"
    )
    self.overall_progress_label.grid(row=0, column=0, padx=5, pady=(5, 2), sticky="w")

    # 整体进度条（较大）
    self.overall_progress_bar = ctk.CTkProgressBar(
        self.progress_frame,
        height=18,
        corner_radius=9
    )
    self.overall_progress_bar.grid(row=1, column=0, padx=5, pady=(0, 8), sticky="ew")
    self.overall_progress_bar.set(0)

    # 当前章节进度标签
    self.chapter_progress_label = ctk.CTkLabel(
        self.progress_frame,
        text="当前章节: 准备中...",
        font=("Microsoft YaHei", 10),
        anchor="w"
    )
    self.chapter_progress_label.grid(row=2, column=0, padx=5, pady=(0, 2), sticky="w")

    # 当前章节进度条（较小）
    self.chapter_progress_bar = ctk.CTkProgressBar(
        self.progress_frame,
        height=12,
        corner_radius=6
    )
    self.chapter_progress_bar.grid(row=3, column=0, padx=5, pady=(0, 5), sticky="ew")
    self.chapter_progress_bar.set(0)

    # 日志文本框标签
    log_label = ctk.CTkLabel(self.center_frame, text="输出日志 (只读)", font=("Microsoft YaHei", 12))
    log_label.grid(row=2, column=0, padx=5, pady=(5, 0), sticky="w")

    # 日志文本框
    self.log_text = ctk.CTkTextbox(self.center_frame, wrap="word", font=("Microsoft YaHei", 12))
    TextWidgetContextMenu(self.log_text)
    self.log_text.grid(row=3, column=0, sticky="nsew", padx=5, pady=(0, 5))
    self.log_text.configure(state="disabled")

def build_right_layout(self):
    """
    右侧区域：小说参数 + 可选功能按钮
    """
    self.right_frame.grid_rowconfigure(0, weight=1)
    self.right_frame.grid_rowconfigure(1, weight=0)
    self.right_frame.columnconfigure(0, weight=1)

    # novel_params_tab.py 的 build_novel_params_area 和 build_optional_buttons_area 会在这里构建
