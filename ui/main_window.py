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
from .ios_theme import apply_ios_theme, IOSColors, IOSLayout, IOSFonts, IOSStyles
from llm_adapters import create_llm_adapter

from prompt_definitions import resolve_global_system_prompt

from config_manager import load_config, save_config, test_llm_config, test_embedding_config
from utils import read_file, save_string_to_txt, clear_file_content
from tooltips import tooltips
from volume_utils import validate_volume_config as validate_vol_config, get_volume_info_text

# 【优化：统一检查 CTkToolTip 导入】
try:
    from CTkToolTip import CTkToolTip
    HAS_TOOLTIP = True
except ImportError:
    HAS_TOOLTIP = False
    logging.warning("CTkToolTip 未安装，悬停提示功能将不可用。建议安装: pip install CTkToolTip")

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
from ui.volume_architecture_tab import build_volume_architecture_tab, load_volume_architecture, save_volume_architecture
from ui.directory_tab import build_directory_tab, load_chapter_blueprint, save_chapter_blueprint
from ui.character_tab import build_character_tab, load_character_state, save_character_state
from ui.summary_tab import build_summary_tab, load_global_summary, save_global_summary
from ui.volume_summary_tab import build_volume_summary_tab, refresh_volume_list, load_volume_summary, save_volume_summary, on_volume_selected
from ui.chapters_tab import build_chapters_tab, refresh_chapters_list, on_chapter_selected, load_chapter_content, save_current_chapter, prev_chapter, next_chapter
from ui.settings_tab import build_settings_tab
from ui.prompt_manager_builder import build_prompt_manager_tab


class NovelGeneratorGUI:
    """
    小说生成器的主GUI类，包含所有的界面布局、事件处理、与后端逻辑的交互等。
    """
    def __init__(self, master):
        self.master = master
        self.master.title("AutoNovel - AI小说生成器")

        # 应用iOS风格主题
        apply_ios_theme()

        # 设置窗口背景色为应用底色
        self.master.configure(fg_color=IOSColors.BG_APP)

        try:
            if os.path.exists("icon.ico"):
                self.master.iconbitmap("icon.ico")
        except Exception:
            pass
        self.master.geometry("1680x920")

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
        # 添加顶部边距，营造iOS风格的留白感
        main_container = ctk.CTkFrame(self.master, fg_color="transparent")
        main_container.pack(fill="both", expand=True, padx=IOSLayout.PADDING_LARGE, pady=IOSLayout.PADDING_LARGE)

        # 【优化：导航栏卡片包裹】
        # 创建卡片容器来包裹整个TabView，使用更明显的边框
        tabview_card = ctk.CTkFrame(
            main_container,
            fg_color="#FFFFFF",  # 纯白卡片背景
            corner_radius=IOSLayout.CORNER_RADIUS_LARGE,
            border_width=2,  # 增加边框宽度，更明显
            border_color="#D1D1D6"  # 使用更深的灰色边框
        )
        tabview_card.pack(fill="both", expand=True)

        self.tabview = ctk.CTkTabview(
            tabview_card,
            corner_radius=IOSLayout.CORNER_RADIUS_LARGE,
            border_width=0,
            height=IOSLayout.TAB_HEIGHT,  # 设置导航栏高度
            # 优化导航栏配色 - 使用更明显的背景色
            segmented_button_fg_color="#F0F0F5",  # 更深的灰色背景，增强对比
            segmented_button_selected_color=IOSColors.PRIMARY,
            segmented_button_selected_hover_color=IOSColors.PRIMARY_HOVER,
            segmented_button_unselected_color="#F0F0F5",
            segmented_button_unselected_hover_color="#E5E5EA",
            text_color=IOSColors.TEXT_SECONDARY,  # 未选中文字颜色
            text_color_disabled=IOSColors.TEXT_TERTIARY,
        )
        self.tabview.pack(fill="both", expand=True)

        # 【优化：设置导航栏字体】
        # 通过访问内部的_segmented_button来设置字体
        try:
            self.tabview._segmented_button.configure(
                font=IOSFonts.get_font(IOSLayout.FONT_SIZE_TAB, "bold")
            )
        except Exception as e:
            pass

        # 【优化：导航栏底部分隔线】
        # 在导航栏下方添加更明显的分隔线，增强层次感
        try:
            # 获取TabView内部的_segmented_button（导航栏）
            nav_button = self.tabview._segmented_button
            # 创建分隔线Frame - 使用2px高度和更深的颜色
            separator = ctk.CTkFrame(
                self.tabview._parent_frame,
                height=2,
                fg_color="#D1D1D6"  # 更深的灰色
            )
            # 将分隔线放置在导航栏下方
            separator.place(relx=0, rely=0, relwidth=1.0, y=IOSLayout.TAB_HEIGHT)
        except Exception as e:
            # 如果访问内部组件失败，静默跳过（不影响功能）
            pass

        # 设置TabView背景为卡片背景色
        self.tabview.configure(fg_color=IOSColors.BG_CARD)

        # 创建各个标签页
        build_main_tab(self)
        build_novel_params_area(self, start_row=0)
        build_optional_buttons_area(self, start_row=1)
        build_setting_tab(self)
        build_volume_architecture_tab(self)
        build_directory_tab(self)
        build_character_tab(self)
        build_summary_tab(self)
        build_volume_summary_tab(self)
        build_chapters_tab(self)
        build_prompt_manager_tab(self)  # 提示词管理放在设置之前
        build_settings_tab(self)

        # 【防呆3：设置小说参数变更监听器】
        from ui.novel_params_tab import setup_novel_params_change_listeners
        setup_novel_params_change_listeners(self)

        # 【优化3：初始加载完成后，标记为已保存状态】
        if hasattr(self, 'save_status_indicator'):
            self.save_status_indicator.set_saved()

        # 【防呆2：启动时检查并更新配置锁定状态】
        if self.filepath_var.get().strip():
            self.check_and_update_config_lock()


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
            # 【防呆2：检查并更新配置锁定状态】
            self.check_and_update_config_lock()

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
            # 【防呆3：设置为保存中状态】
            if hasattr(self, 'save_status_indicator'):
                self.save_status_indicator.set_saving()

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

            # 【防呆2：配置变更检测】
            from ui.validation_utils import validate_config_changes
            filepath = self.filepath_var.get().strip()
            if filepath:
                change_result = validate_config_changes(self.loaded_config, {"other_params": other_params}, filepath)

                if change_result["has_critical_changes"]:
                    # 显示警告对话框
                    warning_msg = "检测到关键配置变更：\n\n"
                    warning_msg += "\n".join(f"• {change}" for change in change_result["changes"])

                    if change_result["warnings"]:
                        warning_msg += "\n\n⚠️ 警告：\n"
                        warning_msg += "\n".join(change_result["warnings"])

                    warning_msg += "\n\n是否继续保存？"

                    if not messagebox.askyesno("配置变更警告", warning_msg, icon='warning'):
                        self.safe_log("❌ 用户取消保存（配置变更检测）")
                        # 【防呆3：恢复未保存状态】
                        if hasattr(self, 'save_status_indicator'):
                            self.save_status_indicator.set_unsaved()
                        return

            # 直接更新内存中的配置，避免覆盖其他修改
            self.loaded_config["other_params"] = other_params

            # 【关键修复】同步回写 characters_involved_var，确保生成流程能读取到最新值
            # 原因：generation_handlers.py:150,735 使用 self.characters_involved_var.get()
            # 而不是直接读取 TextBox，必须保持同步
            self.characters_involved_var.set(other_params["characters_involved"])

            # 保存到配置文件
            save_config(self.loaded_config, self.config_file)

            # 【防呆3：设置为已保存状态】
            if hasattr(self, 'save_status_indicator'):
                self.save_status_indicator.set_saved()

            # 【防呆2：保存后检查配置锁定状态】
            if self.filepath_var.get().strip():
                self.check_and_update_config_lock()

            messagebox.showinfo("提示", "小说参数已保存到配置文件")
            self.safe_log("✅ 小说参数已保存")

        except Exception as e:
            messagebox.showerror("错误", f"保存小说参数失败: {str(e)}")
            self.safe_log(f"❌ 保存小说参数失败: {str(e)}")
            # 【防呆3：保存失败，恢复未保存状态】
            if hasattr(self, 'save_status_indicator'):
                self.save_status_indicator.set_unsaved()

    def check_and_update_config_lock(self):
        """检查并更新配置锁定状态"""
        from ui.validation_utils import check_critical_files_exist

        filepath = self.filepath_var.get().strip()
        if not filepath:
            return

        result = check_critical_files_exist(filepath)

        if result["is_locked"]:
            # 锁定状态
            self.config_locked = True
            self.num_chapters_entry.configure(state="disabled")
            self.num_volumes_entry.configure(state="disabled")
            self.num_chapters_lock_label.configure(text="🔒")
            self.num_volumes_lock_label.configure(text="🔒")
            self.unlock_config_btn.grid()  # 显示解锁按钮

            # 构造锁定原因提示
            lock_reason = []
            if result["directory_exists"]:
                lock_reason.append("已生成章节目录")
            if result["any_chapter_exists"]:
                lock_reason.append("已生成章节")

            tooltip_text = (
                "🔒 此参数已锁定\n\n"
                f"原因：{', '.join(lock_reason)}\n\n"
                "如需修改，请：\n"
                "1. 点击下方\"解锁配置\"按钮\n"
                "2. 或删除相关文件后重新生成"
            )

            # 设置悬停提示（使用 CTkToolTip 如果可用）
            # 只在第一次创建 tooltip，避免重复
            if HAS_TOOLTIP:
                if not hasattr(self, '_tooltips_created'):
                    CTkToolTip(self.num_chapters_lock_label, message=tooltip_text, delay=0.3)
                    CTkToolTip(self.num_volumes_lock_label, message=tooltip_text, delay=0.3)
                    self._tooltips_created = True
        else:
            # 未锁定状态
            self.config_locked = False
            self.num_chapters_entry.configure(state="normal")
            self.num_volumes_entry.configure(state="normal")
            self.num_chapters_lock_label.configure(text="")
            self.num_volumes_lock_label.configure(text="")
            self.unlock_config_btn.grid_remove()  # 隐藏解锁按钮

            # 清除 tooltip 标志，以便重新锁定时可以创建
            if hasattr(self, '_tooltips_created'):
                delattr(self, '_tooltips_created')

    def unlock_critical_config(self):
        """解锁关键配置（带警告对话框）"""
        dialog = ctk.CTkToplevel(self.master)
        dialog.title("警告：解锁关键配置")
        dialog.geometry("500x380")
        dialog.transient(self.master)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (dialog.winfo_screenheight() // 2) - (380 // 2)
        dialog.geometry(f"500x380+{x}+{y}")

        # 标题
        title_label = ctk.CTkLabel(
            dialog,
            text="⚠️ 警告：修改关键配置",
            font=("Microsoft YaHei", 18, "bold"),
            text_color="#FF6347"
        )
        title_label.pack(pady=20)

        # 警告内容
        warning_frame = ctk.CTkFrame(dialog, fg_color="#FFF5EE")
        warning_frame.pack(padx=20, pady=10, fill="both", expand=True)

        warning_text = ctk.CTkTextbox(
            warning_frame,
            font=("Microsoft YaHei", 11),
            wrap="word",
            fg_color="#FFF5EE"
        )
        warning_text.pack(padx=10, pady=10, fill="both", expand=True)

        warning_content = (
            "修改章节数或分卷数可能导致：\n\n"
            "❌ 章节目录与实际不符\n"
            "❌ 分卷架构错乱\n"
            "❌ 向量库元数据不一致\n"
            "❌ 已生成章节无法正确引用\n\n"
            "建议操作：\n"
            "1. 删除 Novel_directory.txt\n"
            "2. 删除 Volume_architecture.txt（如有分卷）\n"
            "3. 重新生成架构和目录\n\n"
            "如果已有章节生成，建议备份后再修改。"
        )
        warning_text.insert("1.0", warning_content)
        warning_text.configure(state="disabled")

        # 按钮区域
        button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        button_frame.pack(pady=15)

        def on_unlock():
            self.config_locked = False
            self.num_chapters_entry.configure(state="normal")
            self.num_volumes_entry.configure(state="normal")
            self.num_chapters_lock_label.configure(text="")
            self.num_volumes_lock_label.configure(text="")
            self.unlock_config_btn.grid_remove()
            self.safe_log("⚠️ 用户已解锁章节数/分卷数配置（高级操作）")
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_unlock = ctk.CTkButton(
            button_frame,
            text="我明白风险，继续解锁",
            command=on_unlock,
            font=("Microsoft YaHei", 12),
            width=160,
            fg_color="#FF6347",
            hover_color="#FF4500"
        )
        btn_unlock.pack(side="left", padx=10)

        btn_cancel = ctk.CTkButton(
            button_frame,
            text="取消",
            command=on_cancel,
            font=("Microsoft YaHei", 12),
            width=100
        )
        btn_cancel.pack(side="left", padx=10)

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)

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
    load_volume_architecture = load_volume_architecture
    save_volume_architecture = save_volume_architecture
    load_chapter_blueprint = load_chapter_blueprint
    save_chapter_blueprint = save_chapter_blueprint
    load_character_state = load_character_state
    save_character_state = save_character_state
    load_global_summary = load_global_summary
    save_global_summary = save_global_summary
    refresh_volume_list = refresh_volume_list
    load_volume_summary = load_volume_summary
    save_volume_summary = save_volume_summary
    on_volume_selected = on_volume_selected
    refresh_chapters_list = refresh_chapters_list
    on_chapter_selected = on_chapter_selected
    save_current_chapter = save_current_chapter
    prev_chapter = prev_chapter
    next_chapter = next_chapter
    test_llm_config = test_llm_config
    test_embedding_config = test_embedding_config
    browse_folder = browse_folder








