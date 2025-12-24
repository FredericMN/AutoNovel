# core/utils/task_queue.py
# -*- coding: utf-8 -*-
"""
任务队列管理器 - 解决GUI线程阻塞问题

核心设计：
1. 使用 queue.Queue 替代 threading.Event 进行线程间通信
2. 所有对话框请求通过队列传递，支持超时机制
3. 后台任务可被取消，支持优雅终止
4. 日志批量缓冲，减少主线程压力
"""

import queue
import threading
import logging
import time
from typing import Optional, Callable, Any, Dict
from dataclasses import dataclass, field
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, Future


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"         # 等待用户交互
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DialogType(Enum):
    """对话框类型枚举"""
    YES_NO = "yes_no"
    OK_CANCEL = "ok_cancel"
    INPUT = "input"
    CUSTOM = "custom"
    CONFLICT = "conflict"      # 批量生成冲突对话框
    CONTINUITY = "continuity"  # 章节连续性检查对话框
    OVERWRITE = "overwrite"    # 覆盖确认对话框
    PROMPT_EDIT = "prompt_edit"  # 提示词编辑对话框


@dataclass
class DialogRequest:
    """对话框请求数据结构"""
    dialog_type: DialogType
    title: str
    message: str
    options: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0  # 默认超时30秒
    default_result: Any = None  # 超时时的默认返回值
    created_at: float = field(default_factory=time.time)  # 请求创建时间

    def get_remaining_timeout(self) -> float:
        """获取剩余超时时间（秒）"""
        elapsed = time.time() - self.created_at
        return max(0, self.timeout - elapsed)


@dataclass
class DialogResponse:
    """对话框响应数据结构"""
    result: Any
    timed_out: bool = False
    cancelled: bool = False


class TaskManager:
    """
    任务管理器 - 管理后台任务和主线程通信

    使用示例：
        manager = TaskManager(master_widget)

        # 在后台线程中请求用户确认
        response = manager.request_dialog(
            DialogRequest(
                dialog_type=DialogType.YES_NO,
                title="确认",
                message="是否继续？",
                timeout=30.0,
                default_result=False
            )
        )

        if response.result:
            # 用户点击是
            ...
    """

    def __init__(self, master_widget=None):
        """
        初始化任务管理器

        Args:
            master_widget: Tkinter主窗口，用于调度主线程任务
        """
        self.master = master_widget

        # 对话框请求队列（后台线程 -> 主线程）
        self._dialog_request_queue: queue.Queue[DialogRequest] = queue.Queue()

        # 对话框响应队列（主线程 -> 后台线程）
        # 使用字典存储每个请求的响应队列，key为请求ID
        self._dialog_response_queues: Dict[int, queue.Queue[DialogResponse]] = {}
        self._response_queue_lock = threading.Lock()
        self._request_counter = 0

        # 任务取消标志
        self._cancel_flags: Dict[str, threading.Event] = {}
        self._cancel_lock = threading.Lock()

        # 日志缓冲队列
        self._log_queue: queue.Queue[str] = queue.Queue()
        self._log_callback: Optional[Callable[[str], None]] = None
        self._log_flush_interval = 0.1  # 100ms刷新一次日志
        self._log_thread: Optional[threading.Thread] = None
        self._log_running = False

        # 线程池（用于并行任务）
        self._executor: Optional[ThreadPoolExecutor] = None
        self._max_workers = 3

        # 主线程对话框处理器
        self._dialog_handlers: Dict[DialogType, Callable] = {}

        # 对话框串行锁：防止 wait_window 期间弹出多个对话框
        self._dialog_processing = False

        # 启动对话框轮询
        if self.master:
            self._start_dialog_polling()

    def set_master(self, master_widget):
        """设置主窗口引用"""
        self.master = master_widget
        self._start_dialog_polling()

    def _start_dialog_polling(self):
        """启动主线程对话框轮询"""
        if not self.master:
            return
        self._poll_dialog_requests()

    def _poll_dialog_requests(self):
        """轮询对话框请求（在主线程中执行）"""
        try:
            # 如果正在处理对话框，跳过本次轮询（避免嵌套弹窗）
            if self._dialog_processing:
                return

            # 非阻塞获取一个请求（串行处理）
            try:
                request_id, request = self._dialog_request_queue.get_nowait()

                # 检查响应队列是否仍存在（如果不存在说明已超时，丢弃请求）
                with self._response_queue_lock:
                    if request_id not in self._dialog_response_queues:
                        logging.debug(f"丢弃已超时的对话框请求: {request.title} (id={request_id})")
                        return  # 丢弃，不弹窗

                self._dialog_processing = True
                try:
                    self._handle_dialog_request(request_id, request)
                finally:
                    self._dialog_processing = False
            except queue.Empty:
                pass
        except Exception as e:
            logging.error(f"对话框轮询异常: {e}")
            self._dialog_processing = False
        finally:
            # 继续轮询（每50ms检查一次）
            if self.master:
                try:
                    self.master.after(50, self._poll_dialog_requests)
                except Exception:
                    pass  # 窗口可能已关闭

    def _handle_dialog_request(self, request_id: int, request: DialogRequest):
        """
        在主线程中处理对话框请求

        Args:
            request_id: 请求ID
            request: 对话框请求
        """
        try:
            # 【幽灵弹窗修复】检查剩余超时时间，若已耗尽则直接返回默认值
            remaining = request.get_remaining_timeout()
            if remaining <= 0:
                logging.warning(f"对话框请求已超时（剩余时间<=0），直接返回默认值: {request.title}")
                self._send_dialog_response(
                    request_id,
                    DialogResponse(result=request.default_result, timed_out=True)
                )
                return

            # 检查是否有注册的处理器
            if request.dialog_type in self._dialog_handlers:
                handler = self._dialog_handlers[request.dialog_type]
                result = handler(request)
                response = DialogResponse(result=result)
            else:
                # 使用默认处理器
                response = self._default_dialog_handler(request)

            # 发送响应
            self._send_dialog_response(request_id, response)

        except Exception as e:
            logging.error(f"处理对话框请求异常: {e}")
            # 发送错误响应
            self._send_dialog_response(
                request_id,
                DialogResponse(result=request.default_result, cancelled=True)
            )

    def _default_dialog_handler(self, request: DialogRequest) -> DialogResponse:
        """
        默认对话框处理器 - 使用自定义 CTkToplevel 实现超时关闭

        注意：此方法在主线程中执行，使用 wait_window() 阻塞
        """
        import customtkinter as ctk

        result = {"value": request.default_result}
        timeout_id = None

        # 【幽灵弹窗修复】使用剩余超时时间
        remaining_timeout = request.get_remaining_timeout()
        if remaining_timeout <= 0:
            logging.warning(f"对话框剩余超时<=0，直接返回默认值: {request.title}")
            return DialogResponse(result=request.default_result, timed_out=True)

        dialog = ctk.CTkToplevel(self.master)
        dialog.title(request.title)
        dialog.geometry("380x180")
        dialog.resizable(False, False)
        dialog.transient(self.master)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (380 // 2)
        y = (dialog.winfo_screenheight() // 2) - (180 // 2)
        dialog.geometry(f"380x180+{x}+{y}")

        # 超时自动关闭（使用剩余时间）
        def on_timeout():
            if dialog.winfo_exists():
                logging.warning(f"对话框超时自动关闭: {request.title}")
                result["value"] = request.default_result
                dialog.destroy()

        timeout_id = dialog.after(int(remaining_timeout * 1000), on_timeout)

        # 消息内容
        ctk.CTkLabel(
            dialog,
            text=request.message,
            wraplength=340,
            justify="center"
        ).pack(pady=(30, 20), padx=20)

        # 按钮区域
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=15)

        def on_yes():
            if timeout_id:
                dialog.after_cancel(timeout_id)
            result["value"] = True
            dialog.destroy()

        def on_no():
            if timeout_id:
                dialog.after_cancel(timeout_id)
            result["value"] = False
            dialog.destroy()

        if request.dialog_type == DialogType.YES_NO:
            yes_text, no_text = "是", "否"
        elif request.dialog_type == DialogType.OK_CANCEL:
            yes_text, no_text = "确定", "取消"
        else:
            yes_text, no_text = "确定", "取消"

        ctk.CTkButton(
            button_frame,
            text=yes_text,
            command=on_yes,
            width=80
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            button_frame,
            text=no_text,
            command=on_no,
            width=80,
            fg_color="gray"
        ).pack(side="left", padx=10)

        dialog.protocol("WM_DELETE_WINDOW", on_no)
        dialog.focus_force()

        # 使用 wait_window 阻塞，但保持事件循环
        dialog.wait_window(dialog)

        return DialogResponse(result=result["value"])

    def _send_dialog_response(self, request_id: int, response: DialogResponse):
        """发送对话框响应到后台线程"""
        with self._response_queue_lock:
            if request_id in self._dialog_response_queues:
                self._dialog_response_queues[request_id].put(response)

    def register_dialog_handler(self, dialog_type: DialogType, handler: Callable):
        """
        注册自定义对话框处理器

        Args:
            dialog_type: 对话框类型
            handler: 处理函数，接收DialogRequest，返回结果
        """
        self._dialog_handlers[dialog_type] = handler

    def _handle_dialog_directly(self, request: DialogRequest) -> DialogResponse:
        """
        在主线程中直接处理对话框（避免队列死锁）

        Args:
            request: 对话框请求

        Returns:
            DialogResponse: 对话框响应
        """
        try:
            if request.dialog_type in self._dialog_handlers:
                handler = self._dialog_handlers[request.dialog_type]
                result = handler(request)
                return DialogResponse(result=result)
            else:
                return self._default_dialog_handler(request)
        except Exception as e:
            logging.error(f"主线程直接处理对话框异常: {e}")
            return DialogResponse(result=request.default_result, cancelled=True)

    def request_dialog(self, request: DialogRequest) -> DialogResponse:
        """
        从后台线程请求显示对话框（阻塞直到用户响应或超时）

        Args:
            request: 对话框请求

        Returns:
            DialogResponse: 对话框响应

        Note:
            如果从主线程调用，将直接处理对话框而不使用队列，避免死锁。
        """
        # 主线程检测：如果在主线程中调用，直接处理对话框
        if threading.current_thread() is threading.main_thread():
            logging.debug("request_dialog 在主线程中调用，直接处理")
            return self._handle_dialog_directly(request)

        # 生成请求ID（后台线程路径）
        with self._response_queue_lock:
            self._request_counter += 1
            request_id = self._request_counter
            response_queue = queue.Queue()
            self._dialog_response_queues[request_id] = response_queue

        try:
            # 发送请求到主线程
            self._dialog_request_queue.put((request_id, request))

            # 等待响应（带超时）
            try:
                response = response_queue.get(timeout=request.timeout)
                return response
            except queue.Empty:
                # 超时
                logging.warning(f"对话框请求超时: {request.title}")
                return DialogResponse(
                    result=request.default_result,
                    timed_out=True
                )
        finally:
            # 清理响应队列
            with self._response_queue_lock:
                self._dialog_response_queues.pop(request_id, None)

    def request_dialog_async(
        self,
        request: DialogRequest,
        callback: Callable[[DialogResponse], None]
    ):
        """
        异步请求对话框（非阻塞）

        Args:
            request: 对话框请求
            callback: 响应回调函数
        """
        def wait_for_response():
            response = self.request_dialog(request)
            # 在主线程中执行回调
            if self.master:
                self.master.after(0, lambda: callback(response))
            else:
                callback(response)

        threading.Thread(target=wait_for_response, daemon=True).start()

    # ========== 任务取消机制 ==========

    def create_cancel_token(self, task_id: str) -> threading.Event:
        """
        创建任务取消令牌

        Args:
            task_id: 任务ID

        Returns:
            threading.Event: 取消事件，set()表示已取消
        """
        with self._cancel_lock:
            cancel_event = threading.Event()
            self._cancel_flags[task_id] = cancel_event
            return cancel_event

    def cancel_task(self, task_id: str):
        """
        取消指定任务

        Args:
            task_id: 任务ID
        """
        with self._cancel_lock:
            if task_id in self._cancel_flags:
                self._cancel_flags[task_id].set()
                logging.info(f"任务已标记为取消: {task_id}")

    def is_cancelled(self, task_id: str) -> bool:
        """
        检查任务是否已取消

        Args:
            task_id: 任务ID

        Returns:
            bool: 是否已取消
        """
        with self._cancel_lock:
            if task_id in self._cancel_flags:
                return self._cancel_flags[task_id].is_set()
            return False

    def cleanup_cancel_token(self, task_id: str):
        """
        清理取消令牌

        Args:
            task_id: 任务ID
        """
        with self._cancel_lock:
            self._cancel_flags.pop(task_id, None)

    # ========== 日志缓冲系统 ==========

    def start_log_buffer(self, callback: Callable[[str], None]):
        """
        启动日志缓冲系统

        Args:
            callback: 日志输出回调（在主线程中执行）
        """
        self._log_callback = callback
        self._log_running = True
        self._log_thread = threading.Thread(target=self._log_flush_loop, daemon=True)
        self._log_thread.start()

    def stop_log_buffer(self):
        """停止日志缓冲系统"""
        self._log_running = False
        if self._log_thread:
            self._log_thread.join(timeout=1.0)

    def _log_flush_loop(self):
        """日志刷新循环"""
        buffer = []
        last_flush = time.time()

        while self._log_running:
            try:
                # 非阻塞获取日志
                try:
                    msg = self._log_queue.get(timeout=self._log_flush_interval)
                    buffer.append(msg)
                except queue.Empty:
                    pass

                # 检查是否需要刷新
                now = time.time()
                should_flush = (
                    len(buffer) >= 10 or  # 缓冲满10条
                    (buffer and now - last_flush >= self._log_flush_interval)  # 超时
                )

                if should_flush and buffer:
                    self._flush_logs(buffer)
                    buffer = []
                    last_flush = now

            except Exception as e:
                logging.error(f"日志刷新异常: {e}")

        # 最终刷新
        if buffer:
            self._flush_logs(buffer)

    def _flush_logs(self, logs: list):
        """刷新日志到主线程"""
        if not self._log_callback or not self.master:
            return

        # 合并日志消息
        combined = "\n".join(logs)

        # 在主线程中执行回调
        try:
            self.master.after(0, lambda: self._log_callback(combined))
        except Exception:
            pass  # 窗口可能已关闭

    def log(self, message: str):
        """
        添加日志消息到缓冲队列

        Args:
            message: 日志消息
        """
        self._log_queue.put(message)

    # ========== 线程池管理 ==========

    def get_executor(self) -> ThreadPoolExecutor:
        """获取线程池执行器"""
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        return self._executor

    def submit_task(self, fn: Callable, *args, **kwargs) -> Future:
        """
        提交任务到线程池

        Args:
            fn: 任务函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            Future: 任务Future对象
        """
        return self.get_executor().submit(fn, *args, **kwargs)

    def shutdown(self):
        """关闭任务管理器"""
        self.stop_log_buffer()
        if self._executor:
            self._executor.shutdown(wait=False)


# 全局任务管理器实例
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """获取全局任务管理器实例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


def init_task_manager(master_widget):
    """
    初始化全局任务管理器

    Args:
        master_widget: Tkinter主窗口
    """
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager(master_widget)
    else:
        _task_manager.set_master(master_widget)
    return _task_manager
