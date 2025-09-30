# ui/ios_theme_helper.py
# -*- coding: utf-8 -*-
"""
iOS风格主题应用辅助工具
用于快速将iOS风格应用到现有页签
"""

import customtkinter as ctk
from ui.ios_theme import IOSColors, IOSLayout, IOSFonts, IOSStyles, create_card_frame, create_section_title


def apply_ios_style_to_simple_tab(tab_widget, title_text=""):
    """
    为简单的文本编辑页签应用iOS风格
    适用于：setting_tab, directory_tab, character_tab, summary_tab, volume_architecture_tab等

    Args:
        tab_widget: 页签控件
        title_text: 可选的标题文本

    Returns:
        dict: 包含常用控件的样式字典
    """
    # 设置页签背景色
    tab_widget.configure(fg_color=IOSColors.BG_PRIMARY)

    return {
        "title_font": IOSFonts.get_font(IOSLayout.FONT_SIZE_MEDIUM, "bold"),
        "button_style": IOSStyles.primary_button(),
        "secondary_button_style": IOSStyles.secondary_button(),
        "textbox_style": IOSStyles.textbox(),
        "label_style": IOSStyles.label_normal(),
        "padding_large": IOSLayout.PADDING_LARGE,
        "padding_medium": IOSLayout.PADDING_MEDIUM,
        "padding_small": IOSLayout.PADDING_SMALL,
    }


def create_ios_button(parent, text, command, style="primary", **kwargs):
    """
    创建iOS风格按钮

    Args:
        parent: 父容器
        text: 按钮文本
        command: 回调函数
        style: 按钮风格 ('primary', 'secondary', 'success', 'danger')
        **kwargs: 其他参数
    """
    if style == "primary":
        btn_style = IOSStyles.primary_button()
    elif style == "secondary":
        btn_style = IOSStyles.secondary_button()
    elif style == "success":
        btn_style = IOSStyles.success_button()
    elif style == "danger":
        btn_style = IOSStyles.danger_button()
    else:
        btn_style = IOSStyles.primary_button()

    btn_style.update(kwargs)
    return ctk.CTkButton(parent, text=text, command=command, **btn_style)


def create_ios_entry(parent, textvariable=None, **kwargs):
    """创建iOS风格输入框"""
    entry_style = IOSStyles.input_entry()
    entry_style.update(kwargs)
    return ctk.CTkEntry(parent, textvariable=textvariable, **entry_style)


def create_ios_textbox(parent, **kwargs):
    """创建iOS风格文本框"""
    textbox_style = IOSStyles.textbox()
    textbox_style.update(kwargs)
    return ctk.CTkTextbox(parent, **textbox_style)


def create_ios_label(parent, text, style="normal", **kwargs):
    """
    创建iOS风格标签

    Args:
        parent: 父容器
        text: 标签文本
        style: 标签风格 ('title', 'normal', 'secondary')
        **kwargs: 其他参数
    """
    if style == "title":
        label_style = IOSStyles.label_title()
    elif style == "normal":
        label_style = IOSStyles.label_normal()
    elif style == "secondary":
        label_style = IOSStyles.label_secondary()
    else:
        label_style = IOSStyles.label_normal()

    label_style.update(kwargs)
    return ctk.CTkLabel(parent, text=text, **label_style)


def create_top_button_bar(parent, buttons_config):
    """
    创建顶部按钮栏（适用于标准页签布局）

    Args:
        parent: 父容器
        buttons_config: 按钮配置列表
            [
                ("按钮文本", callback_function, "primary"),
                ("按钮文本2", callback_function2, "secondary"),
                ...
            ]

    Returns:
        CTkFrame: 按钮栏容器
    """
    button_frame = ctk.CTkFrame(parent, fg_color="transparent")

    for idx, config in enumerate(buttons_config):
        text, command, style = config if len(config) == 3 else (*config, "primary")
        btn = create_ios_button(button_frame, text, command, style)
        btn.pack(side="left", padx=(0, IOSLayout.PADDING_SMALL) if idx < len(buttons_config) - 1 else 0)

    return button_frame


def apply_ios_card_layout(parent_frame, has_header=True, has_scrollbar=False):
    """
    为容器应用卡片式布局

    Args:
        parent_frame: 父容器
        has_header: 是否有顶部标题栏
        has_scrollbar: 是否需要滚动条

    Returns:
        tuple: (header_frame, content_frame) 或 content_frame
    """
    parent_frame.configure(fg_color=IOSColors.BG_SECONDARY, corner_radius=IOSLayout.CORNER_RADIUS_LARGE)

    if has_header:
        header_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        if has_scrollbar:
            content_frame = ctk.CTkScrollableFrame(parent_frame, fg_color="transparent")
        else:
            content_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")

        return header_frame, content_frame
    else:
        if has_scrollbar:
            return ctk.CTkScrollableFrame(parent_frame, fg_color="transparent")
        else:
            return parent_frame


# ========== 预设布局模板 ==========

def build_standard_edit_tab(parent_tab, title, load_callback, save_callback, textbox_var_name="text"):
    """
    构建标准的编辑页签布局（加载-编辑-保存）
    适用于：setting_tab, directory_tab, character_tab, summary_tab等

    Args:
        parent_tab: 页签父容器
        title: 页签标题
        load_callback: 加载按钮回调
        save_callback: 保存按钮回调
        textbox_var_name: 文本框变量名（用于后续访问）

    Returns:
        dict: 包含创建的控件引用
    """
    # 设置页签背景
    parent_tab.configure(fg_color=IOSColors.BG_PRIMARY)
    parent_tab.rowconfigure(0, weight=0)
    parent_tab.rowconfigure(1, weight=1)
    parent_tab.columnconfigure(0, weight=1)

    # 顶部按钮栏
    top_frame = ctk.CTkFrame(parent_tab, fg_color="transparent")
    top_frame.grid(row=0, column=0, sticky="ew", padx=IOSLayout.PADDING_LARGE, pady=(IOSLayout.PADDING_LARGE, IOSLayout.PADDING_SMALL))
    top_frame.columnconfigure(1, weight=1)  # 让中间的字数统计标签占据剩余空间

    # 加载按钮
    load_btn = create_ios_button(top_frame, f"加载 {title}", load_callback, style="primary")
    load_btn.grid(row=0, column=0, sticky="w")

    # 字数统计标签
    word_count_label = create_ios_label(top_frame, "字数：0", style="secondary")
    word_count_label.grid(row=0, column=1, padx=IOSLayout.PADDING_MEDIUM, sticky="w")

    # 保存按钮
    save_btn = create_ios_button(top_frame, "保存修改", save_callback, style="primary")
    save_btn.grid(row=0, column=2, sticky="e")

    # 文本编辑区（卡片样式）
    text_card = create_card_frame(parent_tab)
    text_card.grid(row=1, column=0, sticky="nsew", padx=IOSLayout.PADDING_LARGE, pady=(0, IOSLayout.PADDING_LARGE))
    text_card.rowconfigure(0, weight=1)
    text_card.columnconfigure(0, weight=1)

    textbox = create_ios_textbox(text_card, wrap="word")
    textbox.grid(row=0, column=0, sticky="nsew", padx=IOSLayout.PADDING_LARGE, pady=IOSLayout.PADDING_LARGE)

    # 绑定字数统计
    def update_word_count(event=None):
        text = textbox.get("0.0", "end")
        count = len(text) - 1
        word_count_label.configure(text=f"字数：{count}")

    textbox.bind("<KeyRelease>", update_word_count)
    textbox.bind("<ButtonRelease>", update_word_count)

    return {
        "textbox": textbox,
        "word_count_label": word_count_label,
        "load_btn": load_btn,
        "save_btn": save_btn
    }