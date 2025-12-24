# core/utils/async_dialog.py
# -*- coding: utf-8 -*-
"""
异步对话框工具 - 提供线程安全的对话框显示机制

核心功能：
1. 在后台线程中安全地请求显示对话框
2. 支持超时机制，避免无限等待
3. 提供常用对话框的便捷方法
4. 与TaskManager集成

设计要点：
- 后台线程通过队列发送请求
- 主线程使用 wait_window() 显示对话框（非阻塞事件循环）
- 超时后自动关闭对话框，返回默认值
"""

import logging
from typing import Optional, List
from dataclasses import dataclass
import customtkinter as ctk

from core.utils.task_queue import (
    get_task_manager,
    DialogRequest,
    DialogType
)


@dataclass
class ConflictDialogOptions:
    """批量生成冲突对话框选项"""
    start_chapter: int
    end_chapter: int
    total_chapters: int
    existing_chapters: List[int]


@dataclass
class ContinuityDialogOptions:
    """章节连续性检查对话框选项"""
    chapter_num: int
    message: str
    suggestion: str


@dataclass
class PromptEditDialogOptions:
    """提示词编辑对话框选项"""
    initial_prompt: str
    chapter_num: int


class AsyncDialogHelper:
    """
    异步对话框助手类

    提供在后台线程中安全显示对话框的方法
    """

    def __init__(self, master_widget=None):
        """
        初始化

        Args:
            master_widget: Tkinter主窗口
        """
        self.master = master_widget
        self._task_manager = get_task_manager()

        # 注册自定义对话框处理器
        self._register_handlers()

    def set_master(self, master_widget):
        """设置主窗口引用"""
        self.master = master_widget
        self._task_manager.set_master(master_widget)

    def _register_handlers(self):
        """注册自定义对话框处理器"""
        self._task_manager.register_dialog_handler(
            DialogType.CONFLICT,
            self._handle_conflict_dialog
        )
        self._task_manager.register_dialog_handler(
            DialogType.CONTINUITY,
            self._handle_continuity_dialog
        )
        self._task_manager.register_dialog_handler(
            DialogType.OVERWRITE,
            self._handle_overwrite_dialog
        )
        self._task_manager.register_dialog_handler(
            DialogType.PROMPT_EDIT,
            self._handle_prompt_edit_dialog
        )

    # ========== 便捷方法 ==========

    def ask_yes_no(
        self,
        title: str,
        message: str,
        timeout: float = 30.0,
        default: bool = False
    ) -> bool:
        """
        显示是/否对话框

        Args:
            title: 标题
            message: 消息
            timeout: 超时时间（秒）
            default: 超时时的默认值

        Returns:
            bool: 用户选择结果
        """
        response = self._task_manager.request_dialog(
            DialogRequest(
                dialog_type=DialogType.YES_NO,
                title=title,
                message=message,
                timeout=timeout,
                default_result=default
            )
        )

        if response.timed_out:
            logging.warning(f"对话框超时，使用默认值: {default}")

        return response.result

    def ask_ok_cancel(
        self,
        title: str,
        message: str,
        timeout: float = 30.0,
        default: bool = False
    ) -> bool:
        """
        显示确定/取消对话框

        Args:
            title: 标题
            message: 消息
            timeout: 超时时间（秒）
            default: 超时时的默认值

        Returns:
            bool: 用户选择结果
        """
        response = self._task_manager.request_dialog(
            DialogRequest(
                dialog_type=DialogType.OK_CANCEL,
                title=title,
                message=message,
                timeout=timeout,
                default_result=default
            )
        )

        if response.timed_out:
            logging.warning(f"对话框超时，使用默认值: {default}")

        return response.result

    def ask_conflict_action(
        self,
        options: ConflictDialogOptions,
        timeout: float = 60.0
    ) -> str:
        """
        显示批量生成冲突对话框

        Args:
            options: 冲突选项
            timeout: 超时时间（秒）

        Returns:
            str: 用户选择的操作 ("cancel", "skip", "overwrite")
        """
        response = self._task_manager.request_dialog(
            DialogRequest(
                dialog_type=DialogType.CONFLICT,
                title="批量生成冲突检测",
                message="",
                options={"conflict_options": options},
                timeout=timeout,
                default_result="cancel"
            )
        )

        if response.timed_out:
            logging.warning("冲突对话框超时，默认取消")
            return "cancel"

        return response.result

    def ask_continuity_override(
        self,
        options: ContinuityDialogOptions,
        timeout: float = 60.0
    ) -> bool:
        """
        显示章节连续性检查对话框

        Args:
            options: 连续性选项
            timeout: 超时时间（秒）

        Returns:
            bool: 是否强制继续
        """
        response = self._task_manager.request_dialog(
            DialogRequest(
                dialog_type=DialogType.CONTINUITY,
                title="章节连续性检查",
                message=options.message,
                options={"continuity_options": options},
                timeout=timeout,
                default_result=False
            )
        )

        if response.timed_out:
            logging.warning("连续性检查对话框超时，默认不强制")
            return False

        return response.result

    def ask_overwrite(
        self,
        chapter_num: int,
        timeout: float = 30.0
    ) -> bool:
        """
        显示覆盖确认对话框

        Args:
            chapter_num: 章节号
            timeout: 超时时间（秒）

        Returns:
            bool: 是否覆盖
        """
        response = self._task_manager.request_dialog(
            DialogRequest(
                dialog_type=DialogType.OVERWRITE,
                title="覆盖确认",
                message=f"第{chapter_num}章已存在，是否覆盖？",
                options={"chapter_num": chapter_num},
                timeout=timeout,
                default_result=False
            )
        )

        if response.timed_out:
            logging.warning("覆盖确认对话框超时，默认不覆盖")
            return False

        return response.result

    def edit_prompt(
        self,
        options: PromptEditDialogOptions,
        timeout: float = 300.0  # 提示词编辑给5分钟
    ) -> Optional[str]:
        """
        显示提示词编辑对话框

        Args:
            options: 编辑选项
            timeout: 超时时间（秒）

        Returns:
            Optional[str]: 编辑后的提示词，None表示取消
        """
        response = self._task_manager.request_dialog(
            DialogRequest(
                dialog_type=DialogType.PROMPT_EDIT,
                title="编辑章节提示词",
                message="",
                options={"prompt_options": options},
                timeout=timeout,
                default_result=None
            )
        )

        if response.timed_out:
            logging.warning("提示词编辑对话框超时")
            return None

        return response.result

    # ========== 自定义对话框处理器 ==========
    # 这些处理器在主线程中被调用，使用 wait_window 而不是 event.wait

    def _handle_conflict_dialog(self, request: DialogRequest) -> str:
        """
        处理批量生成冲突对话框

        注意：此方法在主线程中执行，使用 wait_window() 阻塞
        """
        try:
            from ui.ios_theme import IOSFonts
        except ImportError:
            IOSFonts = None

        options: ConflictDialogOptions = request.options.get("conflict_options")
        if not options:
            return "cancel"

        result = {"action": "cancel"}
        timeout_id = None

        # 【幽灵弹窗修复】使用剩余超时时间
        remaining_timeout = request.get_remaining_timeout()
        if remaining_timeout <= 0:
            logging.warning("冲突检测对话框剩余超时<=0，直接返回默认值")
            return "cancel"

        dialog = ctk.CTkToplevel(self.master)
        dialog.title("⚠️ 批量生成冲突检测")
        dialog.geometry("500x300")
        dialog.resizable(False, False)
        dialog.transient(self.master)
        dialog.grab_set()

        # 超时自动关闭
        def on_timeout():
            if dialog.winfo_exists():
                logging.warning("冲突检测对话框超时，自动关闭")
                result["action"] = "cancel"
                dialog.destroy()

        timeout_id = dialog.after(int(remaining_timeout * 1000), on_timeout)

        # 警告信息
        warning_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        warning_frame.pack(fill="both", expand=True, padx=20, pady=20)

        conflict_list = ", ".join([f"第{i}章" for i in options.existing_chapters[:10]])
        if len(options.existing_chapters) > 10:
            conflict_list += f" 等{len(options.existing_chapters)}章"

        font_args = {"font": IOSFonts.get_font(14, "bold")} if IOSFonts else {}
        ctk.CTkLabel(
            warning_frame,
            text=f"⚠️ 检测到 {len(options.existing_chapters)} 个章节已存在！",
            text_color="#FF6B6B",
            **font_args
        ).pack(pady=(0, 10))

        font_args = {"font": IOSFonts.get_font(12)} if IOSFonts else {}
        ctk.CTkLabel(
            warning_frame,
            text=f"范围: 第{options.start_chapter}章 - 第{options.end_chapter}章 (共{options.total_chapters}章)",
            **font_args
        ).pack(pady=5)

        font_args = {"font": IOSFonts.get_font(11)} if IOSFonts else {}
        ctk.CTkLabel(
            warning_frame,
            text=f"冲突章节: {conflict_list}",
            wraplength=450,
            justify="left",
            **font_args
        ).pack(pady=5)

        font_args = {"font": IOSFonts.get_font(10)} if IOSFonts else {}
        ctk.CTkLabel(
            warning_frame,
            text="覆盖将导致：\n1. 旧内容永久丢失\n2. 重复定稿会污染向量库",
            text_color="#FFA500",
            justify="left",
            **font_args
        ).pack(pady=(10, 0))

        # 按钮区
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=(0, 20))

        def on_cancel():
            if timeout_id:
                dialog.after_cancel(timeout_id)
            result["action"] = "cancel"
            dialog.destroy()

        def on_skip():
            if timeout_id:
                dialog.after_cancel(timeout_id)
            result["action"] = "skip"
            dialog.destroy()

        def on_overwrite():
            if timeout_id:
                dialog.after_cancel(timeout_id)
            result["action"] = "overwrite"
            dialog.destroy()

        ctk.CTkButton(
            button_frame,
            text="❌ 取消批量生成",
            command=on_cancel,
            fg_color="#DC3545",
            hover_color="#C82333",
            width=140,
            height=32
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="⏭️ 跳过已存在章节",
            command=on_skip,
            fg_color="#FFC107",
            hover_color="#E0A800",
            width=140,
            height=32
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="⚠️ 覆盖全部",
            command=on_overwrite,
            fg_color="#6C757D",
            hover_color="#5A6268",
            width=140,
            height=32
        ).pack(side="left", padx=5)

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.focus_force()

        # 使用 wait_window 阻塞，但保持事件循环
        dialog.wait_window(dialog)

        return result["action"]

    def _handle_continuity_dialog(self, request: DialogRequest) -> bool:
        """
        处理章节连续性检查对话框

        注意：此方法在主线程中执行，使用 wait_window() 阻塞
        """
        try:
            from ui.ios_theme import IOSFonts
        except ImportError:
            IOSFonts = None

        options: ContinuityDialogOptions = request.options.get("continuity_options")
        if not options:
            return False

        result = {"confirmed": False}
        timeout_id = None

        # 【幽灵弹窗修复】使用剩余超时时间
        remaining_timeout = request.get_remaining_timeout()
        if remaining_timeout <= 0:
            logging.warning("连续性检查对话框剩余超时<=0，直接返回默认值")
            return False

        dialog = ctk.CTkToplevel(self.master)
        dialog.title("章节连续性检查")
        dialog.geometry("450x320")
        dialog.transient(self.master)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (dialog.winfo_screenheight() // 2) - (320 // 2)
        dialog.geometry(f"450x320+{x}+{y}")

        # 超时自动关闭
        def on_timeout():
            if dialog.winfo_exists():
                logging.warning("连续性检查对话框超时，自动关闭")
                result["confirmed"] = False
                dialog.destroy()

        timeout_id = dialog.after(int(remaining_timeout * 1000), on_timeout)

        # 标题
        font_args = {"font": IOSFonts.get_font(16, "bold")} if IOSFonts else {}
        title_label = ctk.CTkLabel(
            dialog,
            text=options.message,
            text_color="#FF6347",
            **font_args
        )
        title_label.pack(pady=15)

        # 建议内容
        suggestion_frame = ctk.CTkFrame(dialog, fg_color="#F5F5F5")
        suggestion_frame.pack(padx=20, pady=10, fill="both", expand=True)

        font_args = {"font": IOSFonts.get_font(11)} if IOSFonts else {}
        suggestion_text = ctk.CTkTextbox(
            suggestion_frame,
            wrap="word",
            height=150,
            fg_color="#F5F5F5",
            **font_args
        )
        suggestion_text.pack(padx=10, pady=10, fill="both", expand=True)
        suggestion_text.insert("1.0", options.suggestion)
        suggestion_text.configure(state="disabled")

        # 按钮区域
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=15)

        def on_force_generate():
            if timeout_id:
                dialog.after_cancel(timeout_id)
            result["confirmed"] = True
            dialog.destroy()

        def on_cancel():
            if timeout_id:
                dialog.after_cancel(timeout_id)
            result["confirmed"] = False
            dialog.destroy()

        font_args = {"font": IOSFonts.get_font(12)} if IOSFonts else {}
        btn_force = ctk.CTkButton(
            button_frame,
            text="强制生成",
            command=on_force_generate,
            width=120,
            fg_color="#FF6347",
            hover_color="#FF4500",
            **font_args
        )
        btn_force.pack(side="left", padx=10)

        btn_cancel = ctk.CTkButton(
            button_frame,
            text="返回修改",
            command=on_cancel,
            width=120,
            **font_args
        )
        btn_cancel.pack(side="left", padx=10)

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.focus_force()

        # 使用 wait_window 阻塞，但保持事件循环
        dialog.wait_window(dialog)

        return result["confirmed"]

    def _handle_overwrite_dialog(self, request: DialogRequest) -> bool:
        """
        处理覆盖确认对话框

        注意：此方法在主线程中执行，使用 wait_window() 阻塞
        """
        try:
            from ui.ios_theme import IOSFonts
        except ImportError:
            IOSFonts = None

        chapter_num = request.options.get("chapter_num", 0)

        result = {"confirmed": False}
        timeout_id = None

        # 【幽灵弹窗修复】使用剩余超时时间
        remaining_timeout = request.get_remaining_timeout()
        if remaining_timeout <= 0:
            logging.warning("覆盖确认对话框剩余超时<=0，直接返回默认值")
            return False

        dialog = ctk.CTkToplevel(self.master)
        dialog.title("覆盖确认")
        dialog.geometry("420x280")
        dialog.resizable(False, False)
        dialog.transient(self.master)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (420 // 2)
        y = (dialog.winfo_screenheight() // 2) - (280 // 2)
        dialog.geometry(f"420x280+{x}+{y}")

        # 超时自动关闭
        def on_timeout():
            if dialog.winfo_exists():
                logging.warning("覆盖确认对话框超时，自动关闭")
                result["confirmed"] = False
                dialog.destroy()

        timeout_id = dialog.after(int(remaining_timeout * 1000), on_timeout)

        # 警告图标和标题
        font_args = {"font": IOSFonts.get_font(16, "bold")} if IOSFonts else {}
        ctk.CTkLabel(
            dialog,
            text=f"⚠️ 第{chapter_num}章已存在！",
            text_color="#FF6B6B",
            **font_args
        ).pack(pady=(20, 10))

        # 警告内容
        warning_frame = ctk.CTkFrame(dialog, fg_color="#FFF5EE")
        warning_frame.pack(padx=20, pady=10, fill="both", expand=True)

        font_args = {"font": IOSFonts.get_font(11)} if IOSFonts else {}
        warning_text = (
            "覆盖将导致：\n"
            "1. 旧内容永久丢失\n"
            "2. 定稿时向量库重复存储（污染检索）\n\n"
            f"建议修改章节号为 {chapter_num + 1}"
        )
        ctk.CTkLabel(
            warning_frame,
            text=warning_text,
            justify="left",
            wraplength=360,
            **font_args
        ).pack(padx=15, pady=15)

        # 按钮区域
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=15)

        def on_yes():
            if timeout_id:
                dialog.after_cancel(timeout_id)
            result["confirmed"] = True
            dialog.destroy()

        def on_no():
            if timeout_id:
                dialog.after_cancel(timeout_id)
            result["confirmed"] = False
            dialog.destroy()

        font_args = {"font": IOSFonts.get_font(12)} if IOSFonts else {}
        ctk.CTkButton(
            button_frame,
            text="是，覆盖",
            command=on_yes,
            fg_color="#FF6347",
            hover_color="#FF4500",
            width=100,
            **font_args
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            button_frame,
            text="否，取消",
            command=on_no,
            width=100,
            **font_args
        ).pack(side="left", padx=10)

        dialog.protocol("WM_DELETE_WINDOW", on_no)
        dialog.focus_force()

        # 使用 wait_window 阻塞，但保持事件循环
        dialog.wait_window(dialog)

        return result["confirmed"]

    def _handle_prompt_edit_dialog(self, request: DialogRequest) -> Optional[str]:
        """
        处理提示词编辑对话框

        注意：此方法在主线程中执行，使用 wait_window() 阻塞
        """
        try:
            from ui.ios_theme import IOSFonts
        except ImportError:
            IOSFonts = None

        options: PromptEditDialogOptions = request.options.get("prompt_options")
        if not options:
            return None

        result = {"prompt": None}
        timeout_id = None

        # 【幽灵弹窗修复】使用剩余超时时间
        remaining_timeout = request.get_remaining_timeout()
        if remaining_timeout <= 0:
            logging.warning("提示词编辑对话框剩余超时<=0，直接返回默认值")
            return None

        dialog = ctk.CTkToplevel(self.master)
        dialog.title("当前章节请求提示词（可编辑）")
        dialog.geometry("600x400")
        dialog.transient(self.master)
        dialog.grab_set()

        # 超时自动关闭
        def on_timeout():
            if dialog.winfo_exists():
                logging.warning("提示词编辑对话框超时，自动关闭")
                result["prompt"] = None
                dialog.destroy()

        timeout_id = dialog.after(int(remaining_timeout * 1000), on_timeout)

        font_args = {"font": IOSFonts.get_font(12)} if IOSFonts else {}
        text_box = ctk.CTkTextbox(dialog, wrap="word", **font_args)
        text_box.pack(fill="both", expand=True, padx=10, pady=10)
        text_box.insert("0.0", options.initial_prompt)

        # 字数统计标签
        font_args = {"font": IOSFonts.get_font(12)} if IOSFonts else {}
        wordcount_label = ctk.CTkLabel(dialog, text="字数：0", **font_args)
        wordcount_label.pack(side="left", padx=(10, 0), pady=5)

        def update_word_count(e=None):
            text = text_box.get("0.0", "end-1c")
            text_length = len(text)
            wordcount_label.configure(text=f"字数：{text_length}")

        text_box.bind("<KeyRelease>", update_word_count)
        text_box.bind("<ButtonRelease>", update_word_count)
        update_word_count()

        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(pady=10)

        def on_confirm():
            if timeout_id:
                dialog.after_cancel(timeout_id)
            result["prompt"] = text_box.get("1.0", "end").strip()
            dialog.destroy()

        def on_cancel():
            if timeout_id:
                dialog.after_cancel(timeout_id)
            result["prompt"] = None
            dialog.destroy()

        font_args = {"font": IOSFonts.get_font(12)} if IOSFonts else {}
        btn_confirm = ctk.CTkButton(
            button_frame, text="确认使用", command=on_confirm, **font_args
        )
        btn_confirm.pack(side="left", padx=10)

        btn_cancel = ctk.CTkButton(
            button_frame, text="取消请求", command=on_cancel, **font_args
        )
        btn_cancel.pack(side="left", padx=10)

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.focus_force()

        # 使用 wait_window 阻塞，但保持事件循环
        dialog.wait_window(dialog)

        return result["prompt"]


# 全局异步对话框助手实例
_dialog_helper: Optional[AsyncDialogHelper] = None


def get_dialog_helper() -> AsyncDialogHelper:
    """获取全局异步对话框助手实例"""
    global _dialog_helper
    if _dialog_helper is None:
        _dialog_helper = AsyncDialogHelper()
    return _dialog_helper


def init_dialog_helper(master_widget) -> AsyncDialogHelper:
    """
    初始化全局异步对话框助手

    Args:
        master_widget: Tkinter主窗口

    Returns:
        AsyncDialogHelper: 对话框助手实例
    """
    global _dialog_helper
    if _dialog_helper is None:
        _dialog_helper = AsyncDialogHelper(master_widget)
    else:
        _dialog_helper.set_master(master_widget)
    return _dialog_helper
