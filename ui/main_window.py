# ui/main_window.py
# -*- coding: utf-8 -*-
import os
import threading
import logging
import traceback
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from .role_library import RoleLibrary
from llm_adapters import create_llm_adapter

from prompt_definitions import resolve_global_system_prompt

from config_manager import load_config, save_config, test_llm_config, test_embedding_config
from utils import read_file, save_string_to_txt, clear_file_content
from tooltips import tooltips
from volume_utils import validate_volume_config as validate_vol_config, get_volume_info_text

from ui.context_menu import TextWidgetContextMenu
from ui.main_tab import build_main_tab, build_left_layout, build_right_layout
from ui.novel_params_tab import build_novel_params_area, build_optional_buttons_area
from ui.generation_handlers import (
    generate_novel_architecture_ui,
    generate_chapter_blueprint_ui,
    generate_chapter_draft_ui,
    finalize_chapter_ui,
    do_consistency_check,
    import_knowledge_handler,
    clear_vectorstore_handler,
    show_plot_arcs_ui,
    generate_batch_ui,
    show_vectorstore_report
)
from ui.setting_tab import build_setting_tab, load_novel_architecture, save_novel_architecture
from ui.directory_tab import build_directory_tab, load_chapter_blueprint, save_chapter_blueprint
from ui.character_tab import build_character_tab, load_character_state, save_character_state
from ui.summary_tab import build_summary_tab, load_global_summary, save_global_summary
from ui.chapters_tab import build_chapters_tab, refresh_chapters_list, on_chapter_selected, load_chapter_content, save_current_chapter, prev_chapter, next_chapter
from ui.settings_tab import build_settings_tab


class NovelGeneratorGUI:
    """
    小说生成器的主GUI类，包含所有的界面布局、事件处理、与后端逻辑的交互等。
    """
    def __init__(self, master):
        self.master = master
        self.master.title("Novel Generator GUI")
        try:
            if os.path.exists("icon.ico"):
                self.master.iconbitmap("icon.ico")
        except Exception:
            pass
        self.master.geometry("1550x840")

        # --------------- 配置文件路径 ---------------
        self.config_file = "config.json"
        self.loaded_config = load_config(self.config_file)

        # 获取上次选中的LLM配置名
        last_selected_llm_config = self.loaded_config.get("last_selected_llm_config", None)

        if self.loaded_config:
            last_llm = next(iter(self.loaded_config["llm_configs"].values())).get("interface_format", "OpenAI")
            last_embedding = self.loaded_config.get("last_embedding_interface_format", "OpenAI")
        else:
            last_llm = "OpenAI"
            last_embedding = "OpenAI"

        # 优先使用上次选中的配置，否则使用第一个配置
        if last_selected_llm_config and last_selected_llm_config in self.loaded_config.get("llm_configs", {}):
            llm_conf = self.loaded_config["llm_configs"][last_selected_llm_config]
            selected_config_name = last_selected_llm_config
        else:
            llm_conf = next(iter(self.loaded_config["llm_configs"].values()))
            selected_config_name = next(iter(self.loaded_config["llm_configs"]))

        choose_configs = self.loaded_config.get("choose_configs", {})


        if self.loaded_config and "embedding_configs" in self.loaded_config and last_embedding in self.loaded_config["embedding_configs"]:
            emb_conf = self.loaded_config["embedding_configs"][last_embedding]
        else:
            emb_conf = {
                "api_key": "",
                "base_url": "https://api.openai.com/v1",
                "model_name": "text-embedding-ada-002",
                "retrieval_k": 4
            }

        # PenBo 增加代理功能支持
        proxy_url = self.loaded_config["proxy_setting"]["proxy_url"]
        proxy_port = self.loaded_config["proxy_setting"]["proxy_port"]
        if self.loaded_config["proxy_setting"]["enabled"]:
            os.environ['HTTP_PROXY'] = f"http://{proxy_url}:{proxy_port}"
            os.environ['HTTPS_PROXY'] = f"http://{proxy_url}:{proxy_port}"
        else:
            os.environ.pop('HTTP_PROXY', None)  
            os.environ.pop('HTTPS_PROXY', None)



        # -- LLM通用参数 --
        self.api_key_var = ctk.StringVar(value=llm_conf.get("api_key", ""))
        self.base_url_var = ctk.StringVar(value=llm_conf.get("base_url", "https://api.openai.com/v1"))
        self.interface_format_var = ctk.StringVar(value=llm_conf.get("interface_format", "OpenAI"))
        self.model_name_var = ctk.StringVar(value=llm_conf.get("model_name", "gpt-4o-mini"))
        self.temperature_var = ctk.DoubleVar(value=llm_conf.get("temperature", 0.7))
        self.max_tokens_var = ctk.IntVar(value=llm_conf.get("max_tokens", 8192))
        self.timeout_var = ctk.IntVar(value=llm_conf.get("timeout", 600))
        self.interface_config_var = ctk.StringVar(value=selected_config_name)  # 使用上次选择的配置名
        self.global_system_prompt_var = ctk.BooleanVar(value=False)


        # -- Embedding相关 --
        self.embedding_interface_format_var = ctk.StringVar(value=last_embedding)
        self.embedding_api_key_var = ctk.StringVar(value=emb_conf.get("api_key", ""))
        self.embedding_url_var = ctk.StringVar(value=emb_conf.get("base_url", "https://api.openai.com/v1"))
        self.embedding_model_name_var = ctk.StringVar(value=emb_conf.get("model_name", "text-embedding-ada-002"))
        self.embedding_retrieval_k_var = ctk.StringVar(value=str(emb_conf.get("retrieval_k", 4)))


        # -- 生成配置相关 --
        self.architecture_llm_var = ctk.StringVar(value=choose_configs.get("architecture_llm", "DeepSeek"))
        self.chapter_outline_llm_var = ctk.StringVar(value=choose_configs.get("chapter_outline_llm", "DeepSeek"))
        self.final_chapter_llm_var = ctk.StringVar(value=choose_configs.get("final_chapter_llm", "DeepSeek"))
        self.consistency_review_llm_var = ctk.StringVar(value=choose_configs.get("consistency_review_llm", "DeepSeek"))
        self.prompt_draft_llm_var = ctk.StringVar(value=choose_configs.get("prompt_draft_llm", "DeepSeek"))





        # -- 小说参数相关 --
        if self.loaded_config and "other_params" in self.loaded_config:
            op = self.loaded_config["other_params"]
            self.topic_default = op.get("topic", "")
            self.genre_var = ctk.StringVar(value=op.get("genre", "玄幻"))
            self.num_chapters_var = ctk.StringVar(value=str(op.get("num_chapters", 10)))
            self.num_volumes_var = ctk.StringVar(value=str(op.get("num_volumes", 0)))  # 新增：分卷数量
            self.word_number_var = ctk.StringVar(value=str(op.get("word_number", 3000)))
            self.filepath_var = ctk.StringVar(value=op.get("filepath", ""))
            self.chapter_num_var = ctk.StringVar(value=str(op.get("chapter_num", "1")))
            self.characters_involved_var = ctk.StringVar(value=op.get("characters_involved", ""))
            self.key_items_var = ctk.StringVar(value=op.get("key_items", ""))
            self.scene_location_var = ctk.StringVar(value=op.get("scene_location", ""))
            self.time_constraint_var = ctk.StringVar(value=op.get("time_constraint", ""))
            self.user_guidance_default = op.get("user_guidance", "")
            self.webdav_url_var = ctk.StringVar(value=op.get("webdav_url", ""))
            self.webdav_username_var = ctk.StringVar(value=op.get("webdav_username", ""))
            self.webdav_password_var = ctk.StringVar(value=op.get("webdav_password", ""))

        else:
            self.topic_default = ""
            self.genre_var = ctk.StringVar(value="玄幻")
            self.num_chapters_var = ctk.StringVar(value="10")
            self.num_volumes_var = ctk.StringVar(value="0")  # 新增：分卷数量默认为0（不分卷）
            self.word_number_var = ctk.StringVar(value="3000")
            self.filepath_var = ctk.StringVar(value="")
            self.chapter_num_var = ctk.StringVar(value="1")
            self.characters_involved_var = ctk.StringVar(value="")
            self.key_items_var = ctk.StringVar(value="")
            self.scene_location_var = ctk.StringVar(value="")
            self.time_constraint_var = ctk.StringVar(value="")
            self.user_guidance_default = ""

        # --------------- 整体Tab布局 ---------------
        self.tabview = ctk.CTkTabview(self.master)
        self.tabview.pack(fill="both", expand=True)

        # 创建各个标签页
        build_main_tab(self)
        build_novel_params_area(self, start_row=0)
        build_optional_buttons_area(self, start_row=1)
        build_setting_tab(self)
        build_directory_tab(self)
        build_character_tab(self)
        build_summary_tab(self)
        build_chapters_tab(self)
        build_settings_tab(self)


    # ----------------- 通用辅助函数 -----------------
    def show_tooltip(self, key: str):
        info_text = tooltips.get(key, "暂无说明")
        messagebox.showinfo("参数说明", info_text)

    def safe_get_int(self, var, default=1):
        try:
            val_str = str(var.get()).strip()
            return int(val_str)
        except:
            var.set(str(default))
            return default

    def log(self, message: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def safe_log(self, message: str):
        self.master.after(0, lambda: self.log(message))

    def disable_button_safe(self, btn):
        self.master.after(0, lambda: btn.configure(state="disabled"))

    def enable_button_safe(self, btn):
        self.master.after(0, lambda: btn.configure(state="normal"))

    def handle_exception(self, context: str):
        full_message = f"{context}\n{traceback.format_exc()}"
        logging.error(full_message)
        self.safe_log(full_message)

    def show_chapter_in_textbox(self, text: str):
        self.chapter_result.delete("0.0", "end")
        self.chapter_result.insert("0.0", text)
        self.chapter_result.see("end")

    # ========== 进度条控制方法 ==========
    def show_progress_bars(self):
        """显示进度条区域"""
        self.master.after(0, lambda: self.progress_frame.grid())

    def hide_progress_bars(self):
        """隐藏进度条区域"""
        self.master.after(0, lambda: self.progress_frame.grid_remove())

    def update_overall_progress(self, current: int, total: int):
        """
        更新整体进度条
        Args:
            current: 已完成章节数
            total: 总章节数
        """
        def update():
            percentage = (current / total * 100) if total > 0 else 0
            self.overall_progress_label.configure(
                text=f"整体进度: {current}/{total} ({percentage:.0f}%)"
            )
            self.overall_progress_bar.set(current / total if total > 0 else 0)
        self.master.after(0, update)

    def update_chapter_progress(self, stage: str, progress: float):
        """
        更新当前章节进度条
        Args:
            stage: 阶段描述（如 "生成草稿" "定稿章节"）
            progress: 进度值 0.0-1.0
        """
        def update():
            self.chapter_progress_label.configure(text=f"当前章节: {stage}")
            self.chapter_progress_bar.set(progress)
        self.master.after(0, update)

    def reset_progress_bars(self):
        """重置进度条"""
        def reset():
            self.overall_progress_label.configure(text="整体进度: 0/0 (0%)")
            self.overall_progress_bar.set(0)
            self.chapter_progress_label.configure(text="当前章节: 准备中...")
            self.chapter_progress_bar.set(0)
        self.master.after(0, reset)

    def test_llm_config(self):
        """
        测试当前的LLM配置是否可用
        """
        interface_format = self.interface_format_var.get().strip()
        api_key = self.api_key_var.get().strip()
        base_url = self.base_url_var.get().strip()
        model_name = self.model_name_var.get().strip()
        temperature = self.temperature_var.get()
        max_tokens = self.max_tokens_var.get()
        timeout = self.timeout_var.get()

        test_llm_config(
            interface_format=interface_format,
            api_key=api_key,
            base_url=base_url,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            log_func=self.safe_log,
            handle_exception_func=self.handle_exception
        )

    def test_embedding_config(self):
        """
        测试当前的Embedding配置是否可用
        """
        api_key = self.embedding_api_key_var.get().strip()
        base_url = self.embedding_url_var.get().strip()
        interface_format = self.embedding_interface_format_var.get().strip()
        model_name = self.embedding_model_name_var.get().strip()

        test_embedding_config(
            api_key=api_key,
            base_url=base_url,
            interface_format=interface_format,
            model_name=model_name,
            log_func=self.safe_log,
            handle_exception_func=self.handle_exception
        )
    
    def browse_folder(self):
        selected_dir = filedialog.askdirectory()
        if selected_dir:
            self.filepath_var.set(selected_dir)
            # 自动加载项目信息
            self.auto_load_project_info(selected_dir)

    def validate_volume_config(self, event=None):
        """
        验证分卷配置的合法性

        验证规则：
        1. 总章节数必须是5的倍数
        2. 如果分卷，检查每卷章节数是否合理
        3. 显示分卷预览
        """
        try:
            num_chapters = self.safe_get_int(self.num_chapters_var, 10)
            num_volumes = self.safe_get_int(self.num_volumes_var, 0)

            # 调用 volume_utils 的验证函数
            is_valid, error_msg = validate_vol_config(num_chapters, num_volumes)

            if not is_valid:
                messagebox.showwarning("配置错误", error_msg)
                return False

            # 如果验证通过且是分卷模式，显示分卷预览
            if num_volumes > 1:
                volume_info = get_volume_info_text(num_chapters, num_volumes)
                self.safe_log(volume_info)

            return True

        except Exception as e:
            self.safe_log(f"⚠ 验证分卷配置时出错: {str(e)}")
            return False

    def auto_load_project_info(self, filepath):
        """自动加载项目信息到界面"""
        import glob

        try:
            # 1. 检测已生成的章节数
            chapters_dir = os.path.join(filepath, "chapters")
            if os.path.exists(chapters_dir):
                chapter_files = glob.glob(os.path.join(chapters_dir, "chapter_*.txt"))
                if chapter_files:
                    max_chapter = max([
                        int(os.path.basename(f).split('_')[1].split('.')[0])
                        for f in chapter_files
                    ])
                    self.chapter_num_var.set(str(max_chapter + 1))  # 设置为下一章
                    self.safe_log(f"✅ 检测到项目已生成 {max_chapter} 章，下一章为第 {max_chapter + 1} 章")

            # 2. 读取Novel_directory.txt并刷新章节列表
            dir_file = os.path.join(filepath, "Novel_directory.txt")
            if os.path.exists(dir_file):
                # 如果有加载章节蓝图的方法，调用它
                if hasattr(self, 'load_chapter_blueprint'):
                    try:
                        self.load_chapter_blueprint()
                        self.safe_log("✅ 已加载章节蓝图")
                    except Exception as e:
                        self.safe_log(f"⚠️ 加载章节蓝图失败: {str(e)}")

            # 3. 读取character_state.txt
            char_file = os.path.join(filepath, "character_state.txt")
            if os.path.exists(char_file):
                if hasattr(self, 'load_character_state'):
                    try:
                        self.load_character_state()
                        self.safe_log("✅ 已加载角色状态")
                    except Exception as e:
                        self.safe_log(f"⚠️ 加载角色状态失败: {str(e)}")

            # 4. 读取global_summary.txt
            summary_file = os.path.join(filepath, "global_summary.txt")
            if os.path.exists(summary_file):
                if hasattr(self, 'load_global_summary'):
                    try:
                        self.load_global_summary()
                        self.safe_log("✅ 已加载前文摘要")
                    except Exception as e:
                        self.safe_log(f"⚠️ 加载前文摘要失败: {str(e)}")

            # 5. 检测向量库
            vectorstore_dir = os.path.join(filepath, "vectorstore")
            if os.path.exists(vectorstore_dir):
                self.safe_log("✅ 检测到向量库存在")

            # 6. 刷新chapters tab的章节列表
            if hasattr(self, 'refresh_chapters_list'):
                try:
                    self.refresh_chapters_list()
                    self.safe_log("✅ 已刷新章节列表")
                except Exception as e:
                    self.safe_log(f"⚠️ 刷新章节列表失败: {str(e)}")

        except Exception as e:
            self.safe_log(f"⚠️ 自动加载项目信息时出错: {str(e)}")

    def show_character_import_window(self):
        """显示角色导入窗口"""
        import_window = ctk.CTkToplevel(self.master)
        import_window.title("导入角色信息")
        import_window.geometry("600x500")
        import_window.transient(self.master)  # 设置为父窗口的临时窗口
        import_window.grab_set()  # 保持窗口在顶层
        
        # 主容器
        main_frame = ctk.CTkFrame(import_window)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 滚动容器
        scroll_frame = ctk.CTkScrollableFrame(main_frame)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # 获取角色库路径
        role_lib_path = os.path.join(self.filepath_var.get().strip(), "角色库")
        self.selected_roles = []  # 存储选中的角色名称
        
        # 动态加载角色分类
        if os.path.exists(role_lib_path):
            # 配置网格布局参数
            scroll_frame.columnconfigure(0, weight=1)
            max_roles_per_row = 4
            current_row = 0
            
            for category in os.listdir(role_lib_path):
                category_path = os.path.join(role_lib_path, category)
                if os.path.isdir(category_path):
                    # 创建分类容器
                    category_frame = ctk.CTkFrame(scroll_frame)
                    category_frame.grid(row=current_row, column=0, sticky="w", pady=(10,5), padx=5)
                    
                    # 添加分类标签
                    category_label = ctk.CTkLabel(category_frame, text=f"【{category}】", 
                                                font=("Microsoft YaHei", 12, "bold"))
                    category_label.grid(row=0, column=0, padx=(0,10), sticky="w")
                    
                    # 初始化角色排列参数
                    role_count = 0
                    row_num = 0
                    col_num = 1  # 从第1列开始（第0列是分类标签）
                    
                    # 添加角色复选框
                    for role_file in os.listdir(category_path):
                        if role_file.endswith(".txt"):
                            role_name = os.path.splitext(role_file)[0]
                            if not any(name == role_name for _, name in self.selected_roles):
                                chk = ctk.CTkCheckBox(category_frame, text=role_name)
                                chk.grid(row=row_num, column=col_num, padx=5, pady=2, sticky="w")
                                self.selected_roles.append((chk, role_name))
                                
                                # 更新行列位置
                                role_count += 1
                                col_num += 1
                                if col_num > max_roles_per_row:
                                    col_num = 1
                                    row_num += 1
                    
                    # 如果没有角色，调整分类标签占满整行
                    if role_count == 0:
                        category_label.grid(columnspan=max_roles_per_row+1, sticky="w")
                    
                    # 更新主布局的行号
                    current_row += 1
                    
                    # 添加分隔线
                    separator = ctk.CTkFrame(scroll_frame, height=1, fg_color="gray")
                    separator.grid(row=current_row, column=0, sticky="ew", pady=5)
                    current_row += 1
        
        # 底部按钮框架
        btn_frame = ctk.CTkFrame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        # 选择按钮
        def confirm_selection():
            selected = [name for chk, name in self.selected_roles if chk.get() == 1]
            self.char_inv_text.delete("0.0", "end")
            self.char_inv_text.insert("0.0", ", ".join(selected))
            import_window.destroy()
            
        btn_confirm = ctk.CTkButton(btn_frame, text="选择", command=confirm_selection)
        btn_confirm.pack(side="left", padx=20)
        
        # 取消按钮
        btn_cancel = ctk.CTkButton(btn_frame, text="取消", command=import_window.destroy)
        btn_cancel.pack(side="right", padx=20)

    def show_role_library(self):
        save_path = self.filepath_var.get().strip()
        if not save_path:
            messagebox.showwarning("警告", "请先设置保存路径")
            return
        
        # 初始化LLM适配器
        llm_adapter = create_llm_adapter(
            interface_format=self.interface_format_var.get(),
            base_url=self.base_url_var.get(),
            model_name=self.model_name_var.get(),
            api_key=self.api_key_var.get(),
            temperature=self.temperature_var.get(),
            max_tokens=self.max_tokens_var.get(),
            timeout=self.timeout_var.get()
        )
        
        # 传递LLM适配器实例到角色库
        if hasattr(self, '_role_lib'):
            if self._role_lib.window and self._role_lib.window.winfo_exists():
                self._role_lib.window.destroy()
        
        system_prompt = resolve_global_system_prompt(self.global_system_prompt_var.get())

        self._role_lib = RoleLibrary(self.master, save_path, llm_adapter, system_prompt=system_prompt)

    def save_other_params(self):
        """保存小说参数到配置文件"""
        try:
            # 从UI组件获取所有参数
            other_params = {
                "topic": self.topic_text.get("0.0", "end").strip(),
                "genre": self.genre_var.get().strip(),
                "num_chapters": self.safe_get_int(self.num_chapters_var, 10),
                "num_volumes": self.safe_get_int(self.num_volumes_var, 0),  # 新增：保存分卷数量
                "word_number": self.safe_get_int(self.word_number_var, 3000),
                "filepath": self.filepath_var.get().strip(),
                "chapter_num": self.chapter_num_var.get().strip(),
                "user_guidance": self.user_guide_text.get("0.0", "end").strip(),
                "characters_involved": self.char_inv_text.get("0.0", "end").strip(),
                "key_items": self.key_items_var.get().strip(),
                "scene_location": self.scene_location_var.get().strip(),
                "time_constraint": self.time_constraint_var.get().strip()
            }

            # 直接更新内存中的配置，避免覆盖其他修改
            self.loaded_config["other_params"] = other_params

            # 【关键修复】同步回写 characters_involved_var，确保生成流程能读取到最新值
            # 原因：generation_handlers.py:150,735 使用 self.characters_involved_var.get()
            # 而不是直接读取 TextBox，必须保持同步
            self.characters_involved_var.set(other_params["characters_involved"])

            # 保存到配置文件
            save_config(self.loaded_config, self.config_file)

            messagebox.showinfo("提示", "小说参数已保存到配置文件")
            self.safe_log("✅ 小说参数已保存")

        except Exception as e:
            messagebox.showerror("错误", f"保存小说参数失败: {str(e)}")
            self.safe_log(f"❌ 保存小说参数失败: {str(e)}")

    # ----------------- 将导入的各模块函数直接赋给类方法 -----------------
    generate_novel_architecture_ui = generate_novel_architecture_ui
    generate_chapter_blueprint_ui = generate_chapter_blueprint_ui
    generate_chapter_draft_ui = generate_chapter_draft_ui
    finalize_chapter_ui = finalize_chapter_ui
    do_consistency_check = do_consistency_check
    generate_batch_ui = generate_batch_ui
    import_knowledge_handler = import_knowledge_handler
    clear_vectorstore_handler = clear_vectorstore_handler
    show_vectorstore_report = show_vectorstore_report
    show_plot_arcs_ui = show_plot_arcs_ui
    load_novel_architecture = load_novel_architecture
    save_novel_architecture = save_novel_architecture
    load_chapter_blueprint = load_chapter_blueprint
    save_chapter_blueprint = save_chapter_blueprint
    load_character_state = load_character_state
    save_character_state = save_character_state
    load_global_summary = load_global_summary
    save_global_summary = save_global_summary
    refresh_chapters_list = refresh_chapters_list
    on_chapter_selected = on_chapter_selected
    save_current_chapter = save_current_chapter
    prev_chapter = prev_chapter
    next_chapter = next_chapter
    test_llm_config = test_llm_config
    test_embedding_config = test_embedding_config
    browse_folder = browse_folder








