# ui/main_tab.py
# -*- coding: utf-8 -*-
import customtkinter as ctk
from tkinter import messagebox
from ui.context_menu import TextWidgetContextMenu
from ui.ios_theme import IOSColors, IOSLayout, IOSFonts, IOSStyles, create_card_frame, create_section_title

def build_main_tab(self):
    """
    主Tab包含三段式布局：左侧本章内容、中间日志与按钮、右侧小说参数
    """
    self.main_tab = self.tabview.add("主界面")
    self.main_tab.configure(fg_color=IOSColors.BG_CARD)  # 使用卡片背景色
    self.main_tab.rowconfigure(0, weight=1)

    # 配置三段列宽：使用更大的最小宽度和更合理的间距
    self.main_tab.columnconfigure(0, weight=1, minsize=500)  # 左侧：本章内容
    self.main_tab.columnconfigure(1, weight=1, minsize=500)  # 中间：日志+按钮
    self.main_tab.columnconfigure(2, weight=1, minsize=500)  # 右侧：小说参数

    # 左侧：本章内容（使用卡片样式）
    self.left_frame = create_card_frame(self.main_tab)
    self.left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, IOSLayout.PADDING_MEDIUM), pady=0)

    # 中间：日志+按钮+进度条（使用卡片样式）
    self.center_frame = create_card_frame(self.main_tab)
    self.center_frame.grid(row=0, column=1, sticky="nsew", padx=(0, IOSLayout.PADDING_MEDIUM), pady=0)

    # 右侧：小说参数（使用卡片样式）
    self.right_frame = create_card_frame(self.main_tab)
    self.right_frame.grid(row=0, column=2, sticky="nsew", padx=0, pady=0)

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

    # 标题使用iOS风格
    self.chapter_label = create_section_title(
        self.left_frame,
        text="本章内容（可编辑）  字数：0",
        font=IOSFonts.get_font(IOSLayout.FONT_SIZE_MEDIUM, "bold")
    )
    self.chapter_label.grid(row=0, column=0, padx=IOSLayout.PADDING_LARGE, pady=(IOSLayout.PADDING_LARGE, IOSLayout.PADDING_SMALL), sticky="w")

    # 章节文本编辑框 - 应用iOS风格
    textbox_style = IOSStyles.textbox()
    self.chapter_result = ctk.CTkTextbox(
        self.left_frame,
        wrap="word",
        **textbox_style
    )
    TextWidgetContextMenu(self.chapter_result)
    self.chapter_result.grid(row=1, column=0, sticky="nsew", padx=IOSLayout.PADDING_LARGE, pady=(0, IOSLayout.PADDING_LARGE))

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

    # Step 按钮区域（两行布局） - 使用透明背景
    self.step_buttons_frame = ctk.CTkFrame(self.center_frame, fg_color="transparent")
    self.step_buttons_frame.grid(row=0, column=0, sticky="ew", padx=IOSLayout.PADDING_LARGE, pady=IOSLayout.PADDING_LARGE)
    self.step_buttons_frame.columnconfigure((0, 1, 2, 3), weight=1)

    # 应用iOS风格按钮样式
    primary_btn_style = IOSStyles.primary_button()

    # 第一行：1-4步骤按钮
    self.btn_generate_architecture = ctk.CTkButton(
        self.step_buttons_frame,
        text="1. 生成架构",
        command=self.generate_novel_architecture_ui,
        **primary_btn_style
    )
    self.btn_generate_architecture.grid(row=0, column=0, padx=(0, IOSLayout.PADDING_SMALL), pady=(0, IOSLayout.PADDING_SMALL), sticky="ew")

    self.btn_generate_directory = ctk.CTkButton(
        self.step_buttons_frame,
        text="2. 生成目录",
        command=self.generate_chapter_blueprint_ui,
        **primary_btn_style
    )
    self.btn_generate_directory.grid(row=0, column=1, padx=(0, IOSLayout.PADDING_SMALL), pady=(0, IOSLayout.PADDING_SMALL), sticky="ew")

    self.btn_generate_chapter = ctk.CTkButton(
        self.step_buttons_frame,
        text="3. 生成草稿",
        command=self.generate_chapter_draft_ui,
        **primary_btn_style
    )
    self.btn_generate_chapter.grid(row=0, column=2, padx=(0, IOSLayout.PADDING_SMALL), pady=(0, IOSLayout.PADDING_SMALL), sticky="ew")

    self.btn_finalize_chapter = ctk.CTkButton(
        self.step_buttons_frame,
        text="4. 定稿章节",
        command=self.finalize_chapter_ui,
        **primary_btn_style
    )
    self.btn_finalize_chapter.grid(row=0, column=3, padx=0, pady=(0, IOSLayout.PADDING_SMALL), sticky="ew")

    # 第二行：批量生成按钮（居中显示） - 使用成功按钮样式
    success_btn_style = IOSStyles.success_button()
    self.btn_batch_generate = ctk.CTkButton(
        self.step_buttons_frame,
        text="✦ 批量生成",
        command=self.generate_batch_ui,
        **success_btn_style
    )
    self.btn_batch_generate.grid(row=1, column=1, columnspan=2, padx=0, pady=0, sticky="ew")

    # 进度条区域（默认隐藏） - 使用iOS风格
    self.progress_frame = ctk.CTkFrame(
        self.center_frame,
        fg_color=IOSColors.BG_TERTIARY,
        corner_radius=IOSLayout.CORNER_RADIUS_MEDIUM
    )
    self.progress_frame.grid(row=1, column=0, sticky="ew", padx=IOSLayout.PADDING_LARGE, pady=(0, IOSLayout.PADDING_MEDIUM))
    self.progress_frame.columnconfigure(0, weight=1)
    self.progress_frame.grid_remove()  # 默认隐藏

    # 顶部行：整体进度标签 + 取消按钮
    progress_header_frame = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
    progress_header_frame.grid(row=0, column=0, sticky="ew", padx=IOSLayout.PADDING_MEDIUM, pady=(IOSLayout.PADDING_MEDIUM, IOSLayout.PADDING_SMALL))
    progress_header_frame.columnconfigure(0, weight=1)

    # 整体进度标签
    label_style = IOSStyles.label_normal()
    self.overall_progress_label = ctk.CTkLabel(
        progress_header_frame,
        text="整体进度: 0/0 (0%)",
        **label_style,
        anchor="w"
    )
    self.overall_progress_label.grid(row=0, column=0, sticky="w")

    # 取消按钮 - 使用警告色
    self.btn_cancel_batch = ctk.CTkButton(
        progress_header_frame,
        text="⏹ 取消",
        width=80,
        height=28,
        fg_color="#FF6B6B",
        hover_color="#FF4757",
        font=IOSFonts.get_font(12),
        command=self.cancel_batch_generation
    )
    self.btn_cancel_batch.grid(row=0, column=1, sticky="e", padx=(IOSLayout.PADDING_MEDIUM, 0))

    # 整体进度条（较大） - 应用iOS风格
    progress_style = IOSStyles.progress_bar()
    progress_style["height"] = 10
    self.overall_progress_bar = ctk.CTkProgressBar(
        self.progress_frame,
        **progress_style
    )
    self.overall_progress_bar.grid(row=1, column=0, padx=IOSLayout.PADDING_MEDIUM, pady=(0, IOSLayout.PADDING_MEDIUM), sticky="ew")
    self.overall_progress_bar.set(0)

    # 当前章节进度标签
    label_secondary_style = IOSStyles.label_secondary()
    self.chapter_progress_label = ctk.CTkLabel(
        self.progress_frame,
        text="当前章节: 准备中...",
        **label_secondary_style,
        anchor="w"
    )
    self.chapter_progress_label.grid(row=2, column=0, padx=IOSLayout.PADDING_MEDIUM, pady=(0, IOSLayout.PADDING_SMALL), sticky="w")

    # 当前章节进度条（较小）
    chapter_progress_style = IOSStyles.progress_bar()
    chapter_progress_style["height"] = 6
    self.chapter_progress_bar = ctk.CTkProgressBar(
        self.progress_frame,
        **chapter_progress_style
    )
    self.chapter_progress_bar.grid(row=3, column=0, padx=IOSLayout.PADDING_MEDIUM, pady=(0, IOSLayout.PADDING_MEDIUM), sticky="ew")
    self.chapter_progress_bar.set(0)

    # 日志文本框标题
    log_label = create_section_title(
        self.center_frame,
        text="输出日志",
        font=IOSFonts.get_font(IOSLayout.FONT_SIZE_MEDIUM, "bold")
    )
    log_label.grid(row=2, column=0, padx=IOSLayout.PADDING_LARGE, pady=(IOSLayout.PADDING_MEDIUM, IOSLayout.PADDING_SMALL), sticky="w")

    # 日志文本框 - 应用iOS风格
    textbox_style = IOSStyles.textbox()
    self.log_text = ctk.CTkTextbox(self.center_frame, wrap="word", **textbox_style)
    TextWidgetContextMenu(self.log_text)
    self.log_text.grid(row=3, column=0, sticky="nsew", padx=IOSLayout.PADDING_LARGE, pady=(0, IOSLayout.PADDING_LARGE))
    self.log_text.configure(state="disabled")

def build_right_layout(self):
    """
    右侧区域：小说参数 + 可选功能按钮
    """
    self.right_frame.grid_rowconfigure(0, weight=1)
    self.right_frame.grid_rowconfigure(1, weight=0)
    self.right_frame.columnconfigure(0, weight=1)

    # novel_params_tab.py 的 build_novel_params_area 和 build_optional_buttons_area 会在这里构建

