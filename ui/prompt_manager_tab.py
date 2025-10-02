# ui/prompt_manager_tab.py
# -*- coding: utf-8 -*-
"""
提示词管理界面
三列布局：模块列表 | 编辑器 | 操作面板
"""
import os
import customtkinter as ctk
from tkinter import messagebox, filedialog
import logging
from core.prompting.prompt_manager import PromptManager
from ui.ios_theme import IOSColors, IOSLayout, IOSStyles

class PromptManagerTab(ctk.CTkFrame):
    """提示词管理页签"""

    # 变量名称的中文说明
    VARIABLE_DESCRIPTIONS = {
        "topic": "小说主题",
        "genre": "小说类型（如玄幻、科幻等）",
        "number_of_chapters": "总章节数",
        "word_number": "每章字数",
        "user_guidance": "用户的额外指导内容",
        "core_seed": "核心种子（主题、冲突）",
        "character_dynamics": "角色动力学设定",
        "world_building": "世界观设定",
        "novel_architecture": "完整的小说架构",
        "num_volumes": "分卷数量",
        "num_chapters": "总章节数",
        "volume_format_examples": "分卷格式示例",
        "start_chapter": "起始章节号",
        "end_chapter": "结束章节号",
        "chapter_text": "章节正文内容",
        "global_summary": "全局前文摘要",
        "old_state": "旧的角色状态",
        "volume_number": "卷号",
        "volume_start": "卷起始章节号（实际生成起点，续写时会跳过已完成章节）",
        "volume_end": "卷结束章节号",
        "volume_total_chapters": "本卷总章数（整卷规划）",
        "volume_chapter_count": "本次待生成章节数（续写时为剩余章节数）",
        "volume_original_start": "本卷原始起始章号（用于判断是否续写）",
        "previous_volumes_summary": "前序卷实际发展摘要",
        "resume_mode_notice": "续写模式提示（仅续写时传入，避免影响上下文）",
        "volume_chapters_text": "卷内所有章节文本",
        "volume_architecture": "分卷架构内容",
        "volume_position": "章节在本卷中的位置（开局/发展/高潮/收束）",
        "chapter_number": "当前章节号",
        "chapter_title": "章节标题",
        "chapter_outline": "章节大纲",
        "retrieved_context": "检索到的历史上下文",
        "character_state": "当前角色状态",
        "plot_arcs": "剧情要点",
        "old_plot_arcs": "旧的剧情要点（详细版）",
        "plot_arcs_text": "剧情要点文本（完整内容）",
        "current_chapter": "当前章节号",
        "classified_plot_arcs": "经过分层标记的剧情要点",
        "unresolved_count": "未解决伏笔数量",
        "resolved_count": "已解决伏笔数量",
        "distilled_arcs": "提炼后的精简伏笔"
    }

    def __init__(self, parent):
        super().__init__(parent, fg_color=IOSColors.BG_PRIMARY)
        self.pm = PromptManager()
        self.current_category = None
        self.current_module = None
        self.is_modified = False  # 跟踪是否有未保存的修改

        self.setup_ui()
        self.load_module_list()

    def setup_ui(self):
        """创建UI布局"""
        # 配置网格权重
        self.grid_columnconfigure(0, weight=0, minsize=250)  # 左侧：模块列表
        self.grid_columnconfigure(1, weight=1)               # 中间：编辑器
        self.grid_columnconfigure(2, weight=0, minsize=280)  # 右侧：操作面板
        self.grid_rowconfigure(0, weight=1)

        # ========== 左侧：模块列表 ==========
        self.setup_left_panel()

        # ========== 中间：编辑器 ==========
        self.setup_center_panel()

        # ========== 右侧：操作面板 ==========
        self.setup_right_panel()

    def setup_left_panel(self):
        """左侧：模块列表"""
        left_frame = ctk.CTkFrame(
            self,
            fg_color=IOSColors.BG_CARD,
            border_width=1,
            border_color=IOSColors.SEPARATOR,
            corner_radius=IOSLayout.CORNER_RADIUS_LARGE
        )
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(IOSLayout.PADDING_LARGE, IOSLayout.PADDING_MEDIUM))

        # 标题
        title_label = ctk.CTkLabel(
            left_frame,
            text="提示词模块",
            font=("Microsoft YaHei", 16, "bold"),
            text_color=IOSColors.TEXT_PRIMARY
        )
        title_label.pack(pady=(15, 10))

        # 滚动框架
        self.modules_scroll = ctk.CTkScrollableFrame(
            left_frame,
            fg_color="transparent",
            scrollbar_button_color=IOSColors.PRIMARY,
            scrollbar_button_hover_color=IOSColors.PRIMARY_HOVER
        )
        self.modules_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def setup_center_panel(self):
        """中间：编辑器区域"""
        center_frame = ctk.CTkFrame(
            self,
            fg_color=IOSColors.BG_CARD,
            border_width=1,
            border_color=IOSColors.SEPARATOR,
            corner_radius=IOSLayout.CORNER_RADIUS_LARGE
        )
        center_frame.grid(row=0, column=1, sticky="nsew", padx=IOSLayout.PADDING_MEDIUM)

        # 配置网格
        center_frame.grid_rowconfigure(1, weight=1)
        center_frame.grid_columnconfigure(0, weight=1)

        # 顶部：标题行
        title_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 10))
        title_frame.grid_columnconfigure(0, weight=1)

        self.editor_title = ctk.CTkLabel(
            title_frame,
            text="选择一个模块开始编辑",
            font=("Microsoft YaHei", 16, "bold"),
            text_color=IOSColors.TEXT_PRIMARY,
            anchor="w"
        )
        self.editor_title.grid(row=0, column=0, sticky="w")

        self.editor_subtitle = ctk.CTkLabel(
            title_frame,
            text="",
            font=("Microsoft YaHei", 11),
            text_color=IOSColors.TEXT_SECONDARY,
            anchor="w"
        )
        self.editor_subtitle.grid(row=1, column=0, sticky="w", pady=(5, 0))

        # 编辑器文本框
        self.editor_textbox = ctk.CTkTextbox(
            center_frame,
            wrap="word",
            font=("Microsoft YaHei", IOSLayout.FONT_SIZE_EDITOR),
            fg_color=IOSColors.BG_CARD,
            border_width=1,
            border_color=IOSColors.SEPARATOR,
            corner_radius=IOSLayout.CORNER_RADIUS_LARGE
        )
        self.editor_textbox.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10))
        self.editor_textbox.bind("<KeyRelease>", self.on_text_modified)

        # 底部：字数统计
        stats_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        stats_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))

        self.word_count_label = ctk.CTkLabel(
            stats_frame,
            text="字数：0",
            font=("Microsoft YaHei", 11),
            text_color=IOSColors.TEXT_SECONDARY
        )
        self.word_count_label.pack(side="left")

        self.modified_indicator = ctk.CTkLabel(
            stats_frame,
            text="",
            font=("Microsoft YaHei", 11),
            text_color=IOSColors.DANGER
        )
        self.modified_indicator.pack(side="right")

    def setup_right_panel(self):
        """右侧：操作面板"""
        right_frame = ctk.CTkFrame(
            self,
            fg_color=IOSColors.BG_CARD,
            border_width=1,
            border_color=IOSColors.SEPARATOR,
            corner_radius=IOSLayout.CORNER_RADIUS_LARGE
        )
        right_frame.grid(row=0, column=2, sticky="nsew", padx=(IOSLayout.PADDING_MEDIUM, IOSLayout.PADDING_LARGE))

        # 标题
        title_label = ctk.CTkLabel(
            right_frame,
            text="操作面板",
            font=("Microsoft YaHei", 16, "bold"),
            text_color=IOSColors.TEXT_PRIMARY
        )
        title_label.pack(pady=(15, 20))

        # 启用开关
        self.enable_switch = ctk.CTkSwitch(
            right_frame,
            text="启用此模块",
            font=("Microsoft YaHei", 12),
            command=self.toggle_module_enabled,
            fg_color="#C7C7CC",  # 关闭时的灰色
            progress_color=IOSColors.SUCCESS  # 开启时的绿色
        )
        self.enable_switch.pack(pady=(0, 20))

        # 模块说明
        self.info_frame = ctk.CTkFrame(right_frame, fg_color="#F5F5F5", corner_radius=8)
        self.info_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.info_title = ctk.CTkLabel(
            self.info_frame,
            text="模块信息",
            font=("Microsoft YaHei", 12, "bold"),
            text_color=IOSColors.TEXT_PRIMARY,
            anchor="w"
        )
        self.info_title.pack(anchor="w", padx=10, pady=(10, 5))

        self.info_text = ctk.CTkLabel(
            self.info_frame,
            text="",
            font=("Microsoft YaHei", 11),
            text_color=IOSColors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=240
        )
        self.info_text.pack(anchor="w", padx=10, pady=(0, 10))

        # 变量说明
        self.vars_frame = ctk.CTkFrame(right_frame, fg_color="#F5F5F5", corner_radius=8)
        self.vars_frame.pack(fill="x", padx=15, pady=(0, 15))

        vars_title = ctk.CTkLabel(
            self.vars_frame,
            text="支持的变量",
            font=("Microsoft YaHei", 12, "bold"),
            text_color=IOSColors.TEXT_PRIMARY,
            anchor="w"
        )
        vars_title.pack(anchor="w", padx=10, pady=(10, 5))

        self.vars_text = ctk.CTkLabel(
            self.vars_frame,
            text="",
            font=("Consolas", 10),
            text_color=IOSColors.TEXT_SECONDARY,
            anchor="w",
            justify="left",
            wraplength=240
        )
        self.vars_text.pack(anchor="w", padx=10, pady=(0, 10))

        # 操作按钮
        btn_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.btn_save = ctk.CTkButton(
            btn_frame,
            text="💾 保存修改",
            command=self.save_current_prompt,
            **IOSStyles.primary_button()
        )
        self.btn_save.pack(fill="x", pady=5)

        self.btn_reset = ctk.CTkButton(
            btn_frame,
            text="🔄 重置为默认",
            command=self.reset_to_default,
            fg_color="#FF9500",
            hover_color="#E68600",
            height=IOSLayout.BUTTON_HEIGHT,
            corner_radius=IOSLayout.CORNER_RADIUS_MEDIUM
        )
        self.btn_reset.pack(fill="x", pady=5)

        self.btn_export = ctk.CTkButton(
            btn_frame,
            text="📤 导出模板",
            command=self.export_prompt,
            fg_color="#8E8E93",
            hover_color="#636366",
            height=IOSLayout.BUTTON_HEIGHT,
            corner_radius=IOSLayout.CORNER_RADIUS_MEDIUM
        )
        self.btn_export.pack(fill="x", pady=5)

        self.btn_import = ctk.CTkButton(
            btn_frame,
            text="📥 导入模板",
            command=self.import_prompt,
            fg_color="#8E8E93",
            hover_color="#636366",
            height=IOSLayout.BUTTON_HEIGHT,
            corner_radius=IOSLayout.CORNER_RADIUS_MEDIUM
        )
        self.btn_import.pack(fill="x", pady=5)

    def load_module_list(self):
        """加载模块列表"""
        modules = self.pm.get_all_modules()

        # 分类名称映射
        category_names = {
            "architecture": "📐 架构生成",
            "blueprint": "📖 目录生成",
            "chapter": "📝 章节生成",
            "finalization": "✅ 定稿阶段",
            "helper": "🔧 辅助功能"
        }

        for category, category_modules in modules.items():
            # 分类标题
            category_label = ctk.CTkLabel(
                self.modules_scroll,
                text=category_names.get(category, category),
                font=("Microsoft YaHei", 13, "bold"),
                text_color=IOSColors.TEXT_PRIMARY,
                anchor="w"
            )
            category_label.pack(fill="x", pady=(10, 5))

            # 模块列表
            for name, info in category_modules.items():
                self.create_module_item(category, name, info)

    def create_module_item(self, category: str, name: str, info: dict):
        """创建单个模块项"""
        item_frame = ctk.CTkFrame(
            self.modules_scroll,
            fg_color="#FFFFFF",
            border_width=1,
            border_color=IOSColors.SEPARATOR,
            corner_radius=8
        )
        item_frame.pack(fill="x", padx=5, pady=3)

        # 左侧：复选框 + 名称
        left_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=8)

        # 复选框
        checkbox = ctk.CTkCheckBox(
            left_frame,
            text="",
            width=20,
            command=lambda: self.toggle_module(category, name, checkbox),
            fg_color=IOSColors.SUCCESS,
            hover_color=IOSColors.SUCCESS
        )
        checkbox.pack(side="left")

        if info["enabled"]:
            checkbox.select()

        # 必需模块禁用复选框
        if info["required"]:
            checkbox.configure(state="disabled")

        # 模块名称
        display_name = info.get("display_name", name)
        if info["required"]:
            display_name = f"🔒 {display_name}"

        name_label = ctk.CTkButton(
            left_frame,
            text=display_name,
            font=("Microsoft YaHei", 11),
            fg_color="transparent",
            text_color=IOSColors.TEXT_PRIMARY,
            hover_color="#E8E8ED",
            anchor="w",
            command=lambda: self.select_module(category, name)
        )
        name_label.pack(side="left", fill="both", expand=True, padx=10)

    def select_module(self, category: str, name: str):
        """选择模块进行编辑"""
        # 检查是否有未保存的修改
        if self.is_modified:
            if not messagebox.askyesno("未保存的修改", "当前提示词有未保存的修改，是否放弃？"):
                return

        self.current_category = category
        self.current_module = name
        self.is_modified = False

        # 加载模块信息
        info = self.pm.get_module_info(category, name)
        if not info:
            return

        # 更新标题
        self.editor_title.configure(text=info.get("display_name", name))
        self.editor_subtitle.configure(text=info.get("description", ""))

        # 加载提示词内容
        prompt = self.pm.get_prompt(category, name)
        self.editor_textbox.delete("1.0", "end")
        if prompt:
            self.editor_textbox.insert("1.0", prompt)

        # 更新启用开关
        self.enable_switch.select() if info["enabled"] else self.enable_switch.deselect()
        if info["required"]:
            self.enable_switch.configure(state="disabled")
        else:
            self.enable_switch.configure(state="normal")

        # 更新模块信息
        self.info_text.configure(text=info.get("description", ""))

        # 更新变量列表
        variables = info.get("variables", [])
        if variables:
            vars_list = []
            for var in variables:
                desc = self.VARIABLE_DESCRIPTIONS.get(var, "")
                if desc:
                    vars_list.append(f"• {{{var}}}\n  → {desc}")
                else:
                    vars_list.append(f"• {{{var}}}")
            vars_str = "\n\n".join(vars_list)  # 使用两个换行增加间距
            self.vars_text.configure(text=vars_str)
        else:
            self.vars_text.configure(text="（无变量）")

        # 更新字数统计
        self.update_word_count()
        self.modified_indicator.configure(text="")

    def on_text_modified(self, event=None):
        """文本修改回调"""
        self.is_modified = True
        self.modified_indicator.configure(text="● 未保存", text_color=IOSColors.DANGER)
        self.update_word_count()

    def update_word_count(self):
        """更新字数统计"""
        text = self.editor_textbox.get("1.0", "end-1c")
        count = len(text)
        self.word_count_label.configure(text=f"字数：{count}")

    def toggle_module(self, category: str, name: str, checkbox):
        """切换模块启用状态"""
        enabled = checkbox.get() == 1
        try:
            self.pm.toggle_module(category, name, enabled)
            status = "启用" if enabled else "禁用"
            logging.info(f"Module {category}.{name} {status}")

            # 如果切换的是当前选中的模块，同步更新右侧开关
            if self.current_category == category and self.current_module == name:
                if enabled:
                    self.enable_switch.select()
                else:
                    self.enable_switch.deselect()
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            checkbox.select()  # 恢复选中状态

    def toggle_module_enabled(self):
        """从开关切换模块启用状态"""
        if not self.current_category or not self.current_module:
            return

        enabled = self.enable_switch.get() == 1
        try:
            self.pm.toggle_module(self.current_category, self.current_module, enabled)
            # 重新加载模块列表以更新复选框状态
            for widget in self.modules_scroll.winfo_children():
                widget.destroy()
            self.load_module_list()
        except ValueError as e:
            messagebox.showerror("错误", str(e))
            self.enable_switch.select() if not enabled else self.enable_switch.deselect()

    def save_current_prompt(self):
        """保存当前提示词"""
        if not self.current_category or not self.current_module:
            messagebox.showwarning("警告", "请先选择一个模块")
            return

        content = self.editor_textbox.get("1.0", "end-1c").strip()
        if not content:
            messagebox.showwarning("警告", "提示词内容不能为空")
            return

        try:
            self.pm.save_custom_prompt(self.current_category, self.current_module, content)
            self.is_modified = False
            self.modified_indicator.configure(text="✅ 已保存", text_color=IOSColors.SUCCESS)
            messagebox.showinfo("成功", "提示词已保存")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {str(e)}")
            logging.error(f"Failed to save prompt: {e}")

    def reset_to_default(self):
        """重置为默认提示词"""
        if not self.current_category or not self.current_module:
            messagebox.showwarning("警告", "请先选择一个模块")
            return

        if not messagebox.askyesno("确认", "确定要重置为默认提示词吗？\n自定义内容将被删除。"):
            return

        try:
            self.pm.reset_to_default(self.current_category, self.current_module)
            # 重新加载
            self.select_module(self.current_category, self.current_module)
            messagebox.showinfo("成功", "已重置为默认提示词")
        except Exception as e:
            messagebox.showerror("错误", f"重置失败: {str(e)}")
            logging.error(f"Failed to reset prompt: {e}")

    def export_prompt(self):
        """导出提示词模板"""
        if not self.current_category or not self.current_module:
            messagebox.showwarning("警告", "请先选择一个模块")
            return

        file_path = filedialog.asksaveasfilename(
            title="导出提示词",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile=f"{self.current_module}_prompt.txt"
        )

        if not file_path:
            return

        try:
            content = self.editor_textbox.get("1.0", "end-1c")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("成功", f"提示词已导出至:\n{file_path}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
            logging.error(f"Failed to export prompt: {e}")

    def import_prompt(self):
        """导入提示词模板"""
        if not self.current_category or not self.current_module:
            messagebox.showwarning("警告", "请先选择一个模块")
            return

        file_path = filedialog.askopenfilename(
            title="导入提示词",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )

        if not file_path:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.editor_textbox.delete("1.0", "end")
            self.editor_textbox.insert("1.0", content)
            self.on_text_modified()  # 标记为已修改
            messagebox.showinfo("成功", "提示词已导入，请点击保存按钮")
        except Exception as e:
            messagebox.showerror("错误", f"导入失败: {str(e)}")
            logging.error(f"Failed to import prompt: {e}")


