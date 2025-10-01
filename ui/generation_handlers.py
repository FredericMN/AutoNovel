# ui/generation_handlers.py
# -*- coding: utf-8 -*-
import os
import threading
import logging
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import traceback
import glob
from prompt_definitions import resolve_global_system_prompt
from utils import read_file, save_string_to_txt, clear_file_content
from novel_generator import (
    Novel_architecture_generate,
    Chapter_blueprint_generate,
    generate_chapter_draft,
    finalize_chapter,
    import_knowledge_file,
    clear_vector_store,
    enrich_chapter_text,
    build_chapter_prompt
)
from consistency_checker import check_consistency
from ui.validation_utils import validate_chapter_continuity

def generate_novel_architecture_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先选择保存文件路径")
        return

    def task():
        confirm = messagebox.askyesno("确认", "确定要生成小说架构吗？")
        if not confirm:
            self.enable_button_safe(self.btn_generate_architecture)
            return

        self.disable_button_safe(self.btn_generate_architecture)
        try:


            interface_format = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["interface_format"]
            api_key = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["api_key"]
            base_url = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["base_url"]
            model_name = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["model_name"]
            temperature = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["temperature"]
            max_tokens = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["max_tokens"]
            timeout_val = self.loaded_config["llm_configs"][self.architecture_llm_var.get()]["timeout"]



            topic = self.topic_text.get("0.0", "end").strip()
            genre = self.genre_var.get().strip()
            num_chapters = self.safe_get_int(self.num_chapters_var, 10)
            num_volumes = self.safe_get_int(self.num_volumes_var, 0)  # 新增：获取分卷数量
            word_number = self.safe_get_int(self.word_number_var, 3000)
            # 获取内容指导
            user_guidance = self.user_guide_text.get("0.0", "end").strip()

            # 强制校验分卷配置
            if not self.validate_volume_config():
                self.enable_button_safe(self.btn_generate_architecture)
                return

            Novel_architecture_generate(
                interface_format=interface_format,
                api_key=api_key,
                base_url=base_url,
                llm_model=model_name,
                topic=topic,
                genre=genre,
                number_of_chapters=num_chapters,
                word_number=word_number,
                filepath=filepath,
                num_volumes=num_volumes,  # 新增：传递分卷数量
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout_val,
                user_guidance=user_guidance,  # 添加内容指导参数
                use_global_system_prompt=None,  # 使用PromptManager配置
                gui_log_callback=self.safe_log  # 传入GUI日志回调
            )
        except Exception:
            self.handle_exception("生成小说架构时出错")
        finally:
            self.enable_button_safe(self.btn_generate_architecture)
    threading.Thread(target=task, daemon=True).start()

def generate_chapter_blueprint_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先选择保存文件路径")
        return

    def task():
        if not messagebox.askyesno("确认", "确定要生成章节目录吗？"):
            self.enable_button_safe(self.btn_generate_chapter)
            return
        self.disable_button_safe(self.btn_generate_directory)
        try:

            number_of_chapters = self.safe_get_int(self.num_chapters_var, 10)
            num_volumes = self.safe_get_int(self.num_volumes_var, 0)  # 新增：获取分卷数量

            interface_format = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["interface_format"]
            api_key = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["api_key"]
            base_url = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["base_url"]
            model_name = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["model_name"]
            temperature = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["temperature"]
            max_tokens = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["max_tokens"]
            timeout_val = self.loaded_config["llm_configs"][self.chapter_outline_llm_var.get()]["timeout"]


            user_guidance = self.user_guide_text.get("0.0", "end").strip()  # 新增获取用户指导

            # 强制校验分卷配置
            if not self.validate_volume_config():
                self.enable_button_safe(self.btn_generate_directory)
                return

            Chapter_blueprint_generate(
                interface_format=interface_format,
                api_key=api_key,
                base_url=base_url,
                llm_model=model_name,
                number_of_chapters=number_of_chapters,
                num_volumes=num_volumes,  # 新增：传递分卷数量
                filepath=filepath,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout_val,
                user_guidance=user_guidance,  # 新增参数
                use_global_system_prompt=None,  # 使用PromptManager配置
                gui_log_callback=self.safe_log  # 传入GUI日志回调
            )
        except Exception:
            self.handle_exception("生成章节蓝图时出错")
        finally:
            self.enable_button_safe(self.btn_generate_directory)
    threading.Thread(target=task, daemon=True).start()

def generate_chapter_draft_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return

    def task():
        self.disable_button_safe(self.btn_generate_chapter)
        try:

            interface_format = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["interface_format"]
            api_key = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["api_key"]
            base_url = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["base_url"]
            model_name = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["model_name"]
            temperature = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["temperature"]
            max_tokens = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["max_tokens"]
            timeout_val = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["timeout"]


            chap_num = self.safe_get_int(self.chapter_num_var, 1)

            # 【防呆1：章节连续性校验】
            validation_result = validate_chapter_continuity(filepath, chap_num)
            if not validation_result["valid"]:
                # 在主线程中显示对话框
                confirm_result = {"confirmed": False}
                confirm_event = threading.Event()

                def ask_continuity_override():
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

                    # 标题
                    title_label = ctk.CTkLabel(
                        dialog,
                        text=validation_result["message"],
                        font=("Microsoft YaHei", 16, "bold"),
                        text_color="#FF6347"
                    )
                    title_label.pack(pady=15)

                    # 建议内容
                    suggestion_frame = ctk.CTkFrame(dialog, fg_color="#F5F5F5")
                    suggestion_frame.pack(padx=20, pady=10, fill="both", expand=True)

                    suggestion_text = ctk.CTkTextbox(
                        suggestion_frame,
                        font=("Microsoft YaHei", 11),
                        wrap="word",
                        height=150,
                        fg_color="#F5F5F5"
                    )
                    suggestion_text.pack(padx=10, pady=10, fill="both", expand=True)
                    suggestion_text.insert("1.0", validation_result["suggestion"])
                    suggestion_text.configure(state="disabled")

                    # 按钮区域
                    button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
                    button_frame.pack(pady=15)

                    def on_force_generate():
                        confirm_result["confirmed"] = True
                        dialog.destroy()
                        confirm_event.set()

                    def on_cancel():
                        confirm_result["confirmed"] = False
                        dialog.destroy()
                        confirm_event.set()

                    btn_force = ctk.CTkButton(
                        button_frame,
                        text="强制生成",
                        command=on_force_generate,
                        font=("Microsoft YaHei", 12),
                        width=120,
                        fg_color="#FF6347",
                        hover_color="#FF4500"
                    )
                    btn_force.pack(side="left", padx=10)

                    btn_cancel = ctk.CTkButton(
                        button_frame,
                        text="返回修改",
                        command=on_cancel,
                        font=("Microsoft YaHei", 12),
                        width=120
                    )
                    btn_cancel.pack(side="left", padx=10)

                    # 关闭窗口时也触发取消
                    dialog.protocol("WM_DELETE_WINDOW", on_cancel)

                self.master.after(0, ask_continuity_override)
                confirm_event.wait()

                if not confirm_result["confirmed"]:
                    self.safe_log(f"❌ 章节连续性检查未通过，用户选择返回修改。")
                    return
                else:
                    self.safe_log(f"⚠️ 用户选择强制生成第{chap_num}章（跳过章节连续性检查）")

            # 【方案A】检查章节文件是否已存在，警告覆盖风险
            chapters_dir = os.path.join(filepath, "chapters")
            os.makedirs(chapters_dir, exist_ok=True)
            chapter_file = os.path.join(chapters_dir, f"chapter_{chap_num}.txt")

            if os.path.exists(chapter_file):
                confirm_result = {"confirmed": False}
                confirm_event = threading.Event()

                def ask_overwrite():
                    result = messagebox.askyesno(
                        "覆盖确认",
                        f"⚠️ 第{chap_num}章已存在！\n\n"
                        f"覆盖将导致：\n"
                        f"1. 旧内容永久丢失\n"
                        f"2. 定稿时向量库重复存储（污染检索）\n\n"
                        f"是否继续？建议修改章节号为 {chap_num + 1}"
                    )
                    confirm_result["confirmed"] = result
                    confirm_event.set()

                self.master.after(0, ask_overwrite)
                confirm_event.wait()

                if not confirm_result["confirmed"]:
                    self.safe_log(f"❌ 用户取消了第{chap_num}章草稿生成，避免覆盖现有内容。")
                    return

            word_number = self.safe_get_int(self.word_number_var, 3000)
            user_guidance = self.user_guide_text.get("0.0", "end").strip()

            char_inv = self.characters_involved_var.get().strip()
            key_items = self.key_items_var.get().strip()
            scene_loc = self.scene_location_var.get().strip()
            time_constr = self.time_constraint_var.get().strip()

            embedding_api_key = self.embedding_api_key_var.get().strip()
            embedding_url = self.embedding_url_var.get().strip()
            embedding_interface_format = self.embedding_interface_format_var.get().strip()
            embedding_model_name = self.embedding_model_name_var.get().strip()
            embedding_k = self.safe_get_int(self.embedding_retrieval_k_var, 4)

            # 获取分卷参数（修复分卷架构信息传递）
            num_volumes = self.safe_get_int(self.num_volumes_var, 0)
            total_chapters = self.safe_get_int(self.num_chapters_var, 0)

            # 调用新添加的 build_chapter_prompt 函数构造初始提示词（包含向量检索过程）
            prompt_text = build_chapter_prompt(
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                filepath=filepath,
                novel_number=chap_num,
                word_number=word_number,
                temperature=temperature,
                user_guidance=user_guidance,
                characters_involved=char_inv,
                key_items=key_items,
                scene_location=scene_loc,
                time_constraint=time_constr,
                embedding_api_key=embedding_api_key,
                embedding_url=embedding_url,
                embedding_interface_format=embedding_interface_format,
                embedding_model_name=embedding_model_name,
                embedding_retrieval_k=embedding_k,
                interface_format=interface_format,
                max_tokens=max_tokens,
                timeout=timeout_val,
                system_prompt=resolve_global_system_prompt(),  # 从PromptManager读取配置
                num_volumes=num_volumes,  # 新增：传递分卷数量
                total_chapters=total_chapters,  # 新增：传递总章节数
                gui_log_callback=self.safe_log  # 传入GUI日志回调，向量检索信息会在这里输出
            )

            # 弹出可编辑提示词对话框，等待用户确认或取消
            result = {"prompt": None}
            event = threading.Event()

            def create_dialog():
                dialog = ctk.CTkToplevel(self.master)
                dialog.title("当前章节请求提示词（可编辑）")
                dialog.geometry("600x400")
                text_box = ctk.CTkTextbox(dialog, wrap="word", font=("Microsoft YaHei", 12))
                text_box.pack(fill="both", expand=True, padx=10, pady=10)

                # 字数统计标签
                wordcount_label = ctk.CTkLabel(dialog, text="字数：0", font=("Microsoft YaHei", 12))
                wordcount_label.pack(side="left", padx=(10,0), pady=5)
                
                # 插入角色内容
                final_prompt = prompt_text
                role_names = [name.strip() for name in self.char_inv_text.get("0.0", "end").strip().split(',') if name.strip()]
                role_lib_path = os.path.join(filepath, "角色库")
                role_contents = []
                
                if os.path.exists(role_lib_path):
                    for root, dirs, files in os.walk(role_lib_path):
                        for file in files:
                            if file.endswith(".txt") and os.path.splitext(file)[0] in role_names:
                                file_path = os.path.join(root, file)
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        role_contents.append(f.read().strip())  # 直接使用文件内容，不添加重复名字
                                except Exception as e:
                                    self.safe_log(f"读取角色文件 {file} 失败: {str(e)}")
                
                if role_contents:
                    role_content_str = "\n".join(role_contents)
                    # 更精确的替换逻辑，处理不同情况下的占位符
                    placeholder_variations = [
                        "核心人物(可能未指定)：{characters_involved}",
                        "核心人物：{characters_involved}",
                        "核心人物(可能未指定):{characters_involved}",
                        "核心人物:{characters_involved}"
                    ]
                    
                    for placeholder in placeholder_variations:
                        if placeholder in final_prompt:
                            final_prompt = final_prompt.replace(
                                placeholder,
                                f"核心人物：\n{role_content_str}"
                            )
                            break
                    else:  # 如果没有找到任何已知占位符变体
                        lines = final_prompt.split('\n')
                        for i, line in enumerate(lines):
                            if "核心人物" in line and "：" in line:
                                lines[i] = f"核心人物：\n{role_content_str}"
                                break
                        final_prompt = '\n'.join(lines)

                text_box.insert("0.0", final_prompt)
                # 更新字数函数
                def update_word_count(event=None):
                    text = text_box.get("0.0", "end-1c")
                    text_length = len(text)
                    wordcount_label.configure(text=f"字数：{text_length}")

                text_box.bind("<KeyRelease>", update_word_count)
                text_box.bind("<ButtonRelease>", update_word_count)
                update_word_count()  # 初始化统计

                button_frame = ctk.CTkFrame(dialog)
                button_frame.pack(pady=10)
                def on_confirm():
                    result["prompt"] = text_box.get("1.0", "end").strip()
                    dialog.destroy()
                    event.set()
                def on_cancel():
                    result["prompt"] = None
                    dialog.destroy()
                    event.set()
                btn_confirm = ctk.CTkButton(button_frame, text="确认使用", font=("Microsoft YaHei", 12), command=on_confirm)
                btn_confirm.pack(side="left", padx=10)
                btn_cancel = ctk.CTkButton(button_frame, text="取消请求", font=("Microsoft YaHei", 12), command=on_cancel)
                btn_cancel.pack(side="left", padx=10)
                # 若用户直接关闭弹窗，则调用 on_cancel 处理
                dialog.protocol("WM_DELETE_WINDOW", on_cancel)
                dialog.grab_set()
            self.master.after(0, create_dialog)
            event.wait()  # 等待用户操作完成
            edited_prompt = result["prompt"]
            if edited_prompt is None:
                self.safe_log("❌ 用户取消了草稿生成请求。")
                return

            from novel_generator.chapter import generate_chapter_draft
            draft_text = generate_chapter_draft(
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                filepath=filepath,
                novel_number=chap_num,
                word_number=word_number,
                temperature=temperature,
                user_guidance=user_guidance,
                characters_involved=char_inv,
                key_items=key_items,
                scene_location=scene_loc,
                time_constraint=time_constr,
                embedding_api_key=embedding_api_key,
                embedding_url=embedding_url,
                embedding_interface_format=embedding_interface_format,
                embedding_model_name=embedding_model_name,
                embedding_retrieval_k=embedding_k,
                interface_format=interface_format,
                max_tokens=max_tokens,
                timeout=timeout_val,
                custom_prompt_text=edited_prompt,  # 使用用户编辑后的提示词
                use_global_system_prompt=None,  # 使用PromptManager配置
                num_volumes=self.safe_get_int(self.num_volumes_var, 0),  # 新增：传递分卷参数
                total_chapters=self.safe_get_int(self.num_chapters_var, 0),  # 新增：传递总章节数
                gui_log_callback=self.safe_log  # 传入GUI日志回调
            )
            if draft_text:
                self.safe_log(f"✅ 第{chap_num}章草稿已保存，请在左侧查看或编辑。")
                self.master.after(0, lambda: self.show_chapter_in_textbox(draft_text))
            else:
                self.safe_log("⚠️ 本章草稿生成失败或无内容。")
        except Exception:
            self.handle_exception("生成章节草稿时出错")
        finally:
            self.enable_button_safe(self.btn_generate_chapter)
    threading.Thread(target=task, daemon=True).start()

def finalize_chapter_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return

    def task():
        if not messagebox.askyesno("确认", "确定要定稿当前章节吗？"):
            self.enable_button_safe(self.btn_finalize_chapter)
            return

        self.disable_button_safe(self.btn_finalize_chapter)
        try:

            interface_format = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["interface_format"]
            api_key = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["api_key"]
            base_url = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["base_url"]
            model_name = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["model_name"]
            temperature = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["temperature"]
            max_tokens = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["max_tokens"]
            timeout_val = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["timeout"]


            embedding_api_key = self.embedding_api_key_var.get().strip()
            embedding_url = self.embedding_url_var.get().strip()
            embedding_interface_format = self.embedding_interface_format_var.get().strip()
            embedding_model_name = self.embedding_model_name_var.get().strip()

            chap_num = self.safe_get_int(self.chapter_num_var, 1)

            # 【方案A】检查章节文件是否已存在，警告覆盖风险
            chapters_dir = os.path.join(filepath, "chapters")
            os.makedirs(chapters_dir, exist_ok=True)
            chapter_file = os.path.join(chapters_dir, f"chapter_{chap_num}.txt")

            # 注意：定稿操作通常是在草稿已存在的前提下进行，但如果用户手动修改章节号
            # 导致定稿一个新的章节号，且该章节号已有定稿内容，则应警告
            # 这里用更温和的提示，因为定稿前通常草稿已经存在
            if os.path.exists(chapter_file):
                # 检查向量库目录，确认是否已定稿过
                vectorstore_dir = os.path.join(filepath, "vectorstore")
                has_vectorstore = os.path.exists(vectorstore_dir) and os.listdir(vectorstore_dir)

                if has_vectorstore:
                    confirm_result = {"confirmed": False}
                    confirm_event = threading.Event()

                    def ask_refinalize():
                        result = messagebox.askyesno(
                            "重复定稿确认",
                            f"⚠️ 第{chap_num}章疑似已定稿过！\n\n"
                            f"重复定稿将导致：\n"
                            f"1. 向量库重复存储相同内容（污染检索）\n"
                            f"2. 摘要和角色状态可能重复更新\n\n"
                            f"是否继续？建议检查章节号是否正确"
                        )
                        confirm_result["confirmed"] = result
                        confirm_event.set()

                    self.master.after(0, ask_refinalize)
                    confirm_event.wait()

                    if not confirm_result["confirmed"]:
                        self.safe_log(f"❌ 用户取消了第{chap_num}章定稿，避免重复写入向量库。")
                        return

            word_number = self.safe_get_int(self.word_number_var, 3000)

            edited_text = self.chapter_result.get("0.0", "end").strip()

            if len(edited_text) < 0.7 * word_number:
                ask = messagebox.askyesno("字数不足", f"当前章节字数 ({len(edited_text)}) 低于目标字数({word_number})的70%，是否要尝试扩写？")
                if ask:
                    self.safe_log("正在扩写章节内容...")
                    enriched = enrich_chapter_text(
                        chapter_text=edited_text,
                        word_number=word_number,
                        api_key=api_key,
                        base_url=base_url,
                        model_name=model_name,
                        temperature=temperature,
                        interface_format=interface_format,
                        max_tokens=max_tokens,
                        timeout=timeout_val,
                        use_global_system_prompt=None  # 使用PromptManager配置
                    )
                    edited_text = enriched
                    self.master.after(0, lambda: self.chapter_result.delete("0.0", "end"))
                    self.master.after(0, lambda: self.chapter_result.insert("0.0", edited_text))
            clear_file_content(chapter_file)
            save_string_to_txt(edited_text, chapter_file)

            # 调用定稿函数，获取成功状态
            success = finalize_chapter(
                novel_number=chap_num,
                word_number=word_number,
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                temperature=temperature,
                filepath=filepath,
                embedding_api_key=embedding_api_key,
                embedding_url=embedding_url,
                embedding_interface_format=embedding_interface_format,
                embedding_model_name=embedding_model_name,
                interface_format=interface_format,
                max_tokens=max_tokens,
                timeout=timeout_val,
                use_global_system_prompt=None,  # 使用PromptManager配置
                num_volumes=self.safe_get_int(self.num_volumes_var, 0),  # 新增：传递分卷参数
                total_chapters=self.safe_get_int(self.num_chapters_var, 0),  # 新增：传递总章节数
                gui_log_callback=self.safe_log  # 传入GUI日志回调
            )

            # 只有定稿成功才更新章节号和显示内容
            if success:
                final_text = read_file(chapter_file)
                self.master.after(0, lambda: self.show_chapter_in_textbox(final_text))

                # 定稿成功后自动递增章节号
                next_chap = chap_num + 1
                self.master.after(0, lambda: self.chapter_num_var.set(str(next_chap)))
                self.safe_log(f"💡 章节号已自动更新为 {next_chap}")
            else:
                self.safe_log("⚠️ 定稿失败，章节号保持不变")
        except Exception:
            self.handle_exception("定稿章节时出错")
        finally:
            self.enable_button_safe(self.btn_finalize_chapter)
    threading.Thread(target=task, daemon=True).start()

def do_consistency_check(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return

    def task():
        self.disable_button_safe(self.btn_check_consistency)
        try:
            interface_format = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["interface_format"]
            api_key = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["api_key"]
            base_url = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["base_url"]
            model_name = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["model_name"]
            temperature = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["temperature"]
            max_tokens = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["max_tokens"]
            timeout = self.loaded_config["llm_configs"][self.consistency_review_llm_var.get()]["timeout"]


            chap_num = self.safe_get_int(self.chapter_num_var, 1)
            chap_file = os.path.join(filepath, "chapters", f"chapter_{chap_num}.txt")
            chapter_text = read_file(chap_file)

            if not chapter_text.strip():
                self.safe_log("⚠️ 当前章节文件为空或不存在，无法审校。")
                return

            self.safe_log("开始一致性审校...")
            result = check_consistency(
                novel_setting="",
                character_state=read_file(os.path.join(filepath, "character_state.txt")),
                global_summary=read_file(os.path.join(filepath, "global_summary.txt")),
                chapter_text=chapter_text,
                api_key=api_key,
                base_url=base_url,
                model_name=model_name,
                temperature=temperature,
                interface_format=interface_format,
                max_tokens=max_tokens,
                timeout=timeout,
                plot_arcs="",
                system_prompt=resolve_global_system_prompt()  # 从PromptManager读取配置
            )
            self.safe_log("审校结果：")
            self.safe_log(result)
        except Exception:
            self.handle_exception("审校时出错")
        finally:
            self.enable_button_safe(self.btn_check_consistency)
    threading.Thread(target=task, daemon=True).start()
def generate_batch_ui(self):
    """批量生成章节（草稿+定稿）"""

    # PenBo 优化界面，使用customtkinter进行批量生成章节界面
    def open_batch_dialog():
        dialog = ctk.CTkToplevel()
        dialog.title("批量生成章节")

        chapter_file = os.path.join(self.filepath_var.get().strip(), "chapters")
        files = glob.glob(os.path.join(chapter_file, "chapter_*.txt"))
        if not files:
            num = 1
        else:
            num = max(int(os.path.basename(f).split('_')[1].split('.')[0]) for f in files) + 1

        dialog.geometry("400x200")
        dialog.resizable(False, False)

        # 创建网格布局
        dialog.grid_columnconfigure(0, weight=0)
        dialog.grid_columnconfigure(1, weight=1)
        dialog.grid_columnconfigure(2, weight=0)
        dialog.grid_columnconfigure(3, weight=1)

        # 起始章节
        ctk.CTkLabel(dialog, text="起始章节:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        entry_start = ctk.CTkEntry(dialog)
        entry_start.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        entry_start.insert(0, str(num))

        # 结束章节
        ctk.CTkLabel(dialog, text="结束章节:").grid(row=0, column=2, padx=10, pady=10, sticky="w")
        entry_end = ctk.CTkEntry(dialog)
        entry_end.grid(row=0, column=3, padx=10, pady=10, sticky="ew")

        # 期望字数
        ctk.CTkLabel(dialog, text="期望字数:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        entry_word = ctk.CTkEntry(dialog)
        entry_word.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        entry_word.insert(0, self.word_number_var.get())

        # 最低字数
        ctk.CTkLabel(dialog, text="最低字数:").grid(row=1, column=2, padx=10, pady=10, sticky="w")
        entry_min = ctk.CTkEntry(dialog)
        entry_min.grid(row=1, column=3, padx=10, pady=10, sticky="ew")
        entry_min.insert(0, self.word_number_var.get())

        # 自动扩写选项
        auto_enrich_bool = ctk.BooleanVar()
        auto_enrich_bool_ck = ctk.CTkCheckBox(dialog, text="低于最低字数时自动扩写", variable=auto_enrich_bool)
        auto_enrich_bool_ck.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        result = {"start": None, "end": None, "word": None, "min": None, "auto_enrich": None, "close": False}

        def on_confirm():
            nonlocal result
            if not entry_start.get() or not entry_end.get() or not entry_word.get() or not entry_min.get():
                messagebox.showwarning("警告", "请填写完整信息。")
                return

            result = {
                "start": entry_start.get(),
                "end": entry_end.get(),
                "word": entry_word.get(),
                "min": entry_min.get(),
                "auto_enrich": auto_enrich_bool.get(),
                "close": False
            }
            dialog.destroy()

        def on_cancel():
            nonlocal result
            result["close"] = True
            dialog.destroy()

        # 按钮框架
        button_frame = ctk.CTkFrame(dialog)
        button_frame.grid(row=3, column=0, columnspan=4, padx=10, pady=10, sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(button_frame, text="确认", command=on_confirm).grid(row=0, column=0, padx=10, pady=10, sticky="e")
        ctk.CTkButton(button_frame, text="取消", command=on_cancel).grid(row=0, column=1, padx=10, pady=10, sticky="w")

        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        dialog.transient(self.master)
        dialog.grab_set()
        dialog.wait_window(dialog)
        return result

    # 1. 打开对话框获取参数
    result = open_batch_dialog()
    if result["close"]:
        return

    # 2. 定义后台任务
    def batch_task():
        try:
            # 禁用批量生成按钮
            self.disable_button_safe(self.btn_batch_generate)

            # 显示进度条
            self.show_progress_bars()
            self.reset_progress_bars()

            start = int(result["start"])
            end = int(result["end"])
            word = int(result["word"])
            min_word = int(result["min"])
            auto_enrich = result["auto_enrich"]
            total = end - start + 1

            # 参数校验
            if start > end:
                self.safe_log("❌ 错误：起始章节不能大于结束章节")
                return

            # 【方案A-批量版】检查范围内章节文件冲突
            filepath = self.filepath_var.get().strip()
            chapters_dir = os.path.join(filepath, "chapters")
            os.makedirs(chapters_dir, exist_ok=True)

            existing_chapters = []
            for i in range(start, end + 1):
                chapter_file = os.path.join(chapters_dir, f"chapter_{i}.txt")
                if os.path.exists(chapter_file):
                    existing_chapters.append(i)

            # 如果有冲突章节，弹出对话框
            if existing_chapters:
                conflict_action = {"action": None}
                conflict_event = threading.Event()

                def show_conflict_dialog():
                    conflict_list = ", ".join([f"第{i}章" for i in existing_chapters[:10]])
                    if len(existing_chapters) > 10:
                        conflict_list += f" 等{len(existing_chapters)}章"

                    dialog = ctk.CTkToplevel()
                    dialog.title("⚠️ 批量生成冲突检测")
                    dialog.geometry("500x300")
                    dialog.resizable(False, False)

                    # 警告信息
                    warning_frame = ctk.CTkFrame(dialog, fg_color="transparent")
                    warning_frame.pack(fill="both", expand=True, padx=20, pady=20)

                    ctk.CTkLabel(
                        warning_frame,
                        text=f"⚠️ 检测到 {len(existing_chapters)} 个章节已存在！",
                        font=("Microsoft YaHei", 14, "bold"),
                        text_color="#FF6B6B"
                    ).pack(pady=(0, 10))

                    ctk.CTkLabel(
                        warning_frame,
                        text=f"范围: 第{start}章 - 第{end}章 (共{total}章)",
                        font=("Microsoft YaHei", 12)
                    ).pack(pady=5)

                    ctk.CTkLabel(
                        warning_frame,
                        text=f"冲突章节: {conflict_list}",
                        font=("Microsoft YaHei", 11),
                        wraplength=450,
                        justify="left"
                    ).pack(pady=5)

                    ctk.CTkLabel(
                        warning_frame,
                        text="覆盖将导致：\n1. 旧内容永久丢失\n2. 重复定稿会污染向量库",
                        font=("Microsoft YaHei", 10),
                        text_color="#FFA500",
                        justify="left"
                    ).pack(pady=(10, 0))

                    # 按钮区
                    button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
                    button_frame.pack(pady=(0, 20))

                    def on_cancel():
                        conflict_action["action"] = "cancel"
                        dialog.destroy()
                        conflict_event.set()

                    def on_skip():
                        conflict_action["action"] = "skip"
                        dialog.destroy()
                        conflict_event.set()

                    def on_overwrite():
                        conflict_action["action"] = "overwrite"
                        dialog.destroy()
                        conflict_event.set()

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
                    dialog.transient(self.master)
                    dialog.grab_set()

                self.master.after(0, show_conflict_dialog)
                conflict_event.wait()

                action = conflict_action["action"]
                if action == "cancel":
                    self.safe_log("❌ 用户取消批量生成，避免覆盖现有章节。")
                    return
                elif action == "skip":
                    self.safe_log(f"⏭️ 用户选择跳过已存在的 {len(existing_chapters)} 个章节")
                    skip_chapters = set(existing_chapters)
                elif action == "overwrite":
                    self.safe_log(f"⚠️ 用户选择覆盖全部 {len(existing_chapters)} 个已存在章节")
                    skip_chapters = set()
            else:
                skip_chapters = set()

            # 输出批量生成开始信息
            self.safe_log("\n" + "=" * 70)
            self.safe_log("📚 开始批量生成章节")
            self.safe_log("=" * 70)
            self.safe_log(f"   起始章节: 第{start}章")
            self.safe_log(f"   结束章节: 第{end}章")
            self.safe_log(f"   总计: {total}章")
            self.safe_log(f"   期望字数: {word}字/章")
            self.safe_log(f"   最低字数: {min_word}字/章")
            self.safe_log(f"   自动扩写: {'是' if auto_enrich else '否'}")
            self.safe_log("=" * 70 + "\n")

            # 批量生成循环
            processed_count = 0  # 实际处理成功的章节数
            skipped_count = 0  # 跳过的章节数
            failed = False  # 标记是否有失败
            actual_total = total - len(skip_chapters)  # 实际需要处理的章节数

            for i in range(start, end + 1):
                # 跳过已存在的章节（如果用户选择跳过）
                if i in skip_chapters:
                    self.safe_log(f"⏭️ 跳过第{i}章（已存在）")
                    skipped_count += 1
                    continue

                # 更新整体进度（处理前）
                self.update_overall_progress(processed_count, actual_total)

                self.safe_log("\n" + "━" * 70)
                self.safe_log(f"▶▶▶ 第{i}章 [{processed_count + 1}/{actual_total}] 开始处理")
                self.safe_log("━" * 70 + "\n")

                try:
                    # 调用单章生成函数（带重试机制）
                    generate_chapter_batch_with_retry(
                        self,
                        chapter_num=i,
                        word=word,
                        min_word=min_word,
                        auto_enrich=auto_enrich,
                        current_index=processed_count + 1,
                        total=actual_total
                    )

                    # 成功后递增计数
                    processed_count += 1

                    # 更新整体进度（处理后）
                    self.update_overall_progress(processed_count, actual_total)

                    self.safe_log("\n" + "━" * 70)
                    self.safe_log(f"✅ 第{i}章处理完成")
                    self.safe_log("━" * 70 + "\n")

                except Exception as e:
                    self.safe_log(f"\n❌ 第{i}章生成失败（已重试）: {str(e)}")
                    self.safe_log("批量生成中止。\n")
                    logging.error(f"Chapter {i} batch generation failed after retry: {str(e)}")
                    failed = True
                    break

            # 输出完成信息
            self.safe_log("\n" + "=" * 70)
            if failed:
                self.safe_log("⚠️  批量生成部分完成（遇到错误已中止）")
                self.safe_log(f"   成功处理: {processed_count}章")
                self.safe_log(f"   失败章节: 第{i}章")
                if skipped_count > 0:
                    self.safe_log(f"   跳过章节: {skipped_count}章")
            else:
                self.safe_log("🎉 批量生成完成！")
                self.safe_log(f"   成功处理: {processed_count}章")
                if skipped_count > 0:
                    self.safe_log(f"   跳过章节: {skipped_count}章")
            self.safe_log("=" * 70 + "\n")

        except Exception as e:
            self.handle_exception("批量生成时出错")
        finally:
            # 隐藏进度条
            self.hide_progress_bars()
            # 启用批量生成按钮
            self.enable_button_safe(self.btn_batch_generate)

    # 3. 启动后台线程
    threading.Thread(target=batch_task, daemon=True).start()


def generate_chapter_batch_with_retry(
    self,
    chapter_num: int,
    word: int,
    min_word: int,
    auto_enrich: bool,
    current_index: int,
    total: int
):
    """
    单章批量生成函数（带重试机制）

    Args:
        chapter_num: 章节号
        word: 期望字数
        min_word: 最低字数
        auto_enrich: 是否自动扩写
        current_index: 当前处理索引（用于进度显示）
        total: 总章节数
    """
    max_retries = 1  # 最多重试1次

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                self.safe_log(f"\n🔄 第{chapter_num}章生成失败，开始第{attempt}次重试...\n")

            # 调用单章生成核心逻辑
            generate_single_chapter_batch(
                self,
                chapter_num=chapter_num,
                word=word,
                min_word=min_word,
                auto_enrich=auto_enrich,
                current_index=current_index,
                total=total
            )

            # 成功则退出
            return

        except Exception as e:
            if attempt < max_retries:
                self.safe_log(f"⚠️  生成出错: {str(e)}")
                self.safe_log(f"   准备重试...")

                # 如果生成过程中已经污染了向量库，需要回滚
                # 但由于向量库没有事务机制，我们在第二次尝试时避免更新向量库
                continue
            else:
                # 重试后仍失败，抛出异常
                raise Exception(f"生成失败（已重试{max_retries}次）: {str(e)}")


def generate_single_chapter_batch(
    self,
    chapter_num: int,
    word: int,
    min_word: int,
    auto_enrich: bool,
    current_index: int,
    total: int
):
    """
    单章批量生成核心逻辑（不含重试）

    包含3个阶段:
    1. 构建提示词（含向量检索）
    2. 生成草稿
    3. 定稿章节
    """
    # 获取草稿生成配置
    draft_interface_format = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["interface_format"]
    draft_api_key = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["api_key"]
    draft_base_url = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["base_url"]
    draft_model_name = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["model_name"]
    draft_temperature = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["temperature"]
    draft_max_tokens = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["max_tokens"]
    draft_timeout = self.loaded_config["llm_configs"][self.prompt_draft_llm_var.get()]["timeout"]

    # 获取定稿配置
    finalize_interface_format = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["interface_format"]
    finalize_api_key = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["api_key"]
    finalize_base_url = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["base_url"]
    finalize_model_name = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["model_name"]
    finalize_temperature = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["temperature"]
    finalize_max_tokens = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["max_tokens"]
    finalize_timeout = self.loaded_config["llm_configs"][self.final_chapter_llm_var.get()]["timeout"]

    # 获取其他参数
    user_guidance = self.user_guide_text.get("0.0", "end").strip()
    char_inv = self.characters_involved_var.get().strip()
    key_items = self.key_items_var.get().strip()
    scene_loc = self.scene_location_var.get().strip()
    time_constr = self.time_constraint_var.get().strip()

    embedding_api_key = self.embedding_api_key_var.get().strip()
    embedding_url = self.embedding_url_var.get().strip()
    embedding_interface_format = self.embedding_interface_format_var.get().strip()
    embedding_model_name = self.embedding_model_name_var.get().strip()
    embedding_k = self.safe_get_int(self.embedding_retrieval_k_var, 4)

    # 获取分卷参数（修复分卷架构信息传递）
    num_volumes = self.safe_get_int(self.num_volumes_var, 0)
    total_chapters = self.safe_get_int(self.num_chapters_var, 0)

    # ========== 阶段1: 构建提示词（含向量检索） ==========
    self.update_chapter_progress("准备中...", 0.0)
    self.safe_log("▶ [阶段1/3] 构建章节提示词")

    prompt_text = build_chapter_prompt(
        api_key=draft_api_key,
        base_url=draft_base_url,
        model_name=draft_model_name,
        filepath=self.filepath_var.get().strip(),
        novel_number=chapter_num,
        word_number=word,
        temperature=draft_temperature,
        user_guidance=user_guidance,
        characters_involved=char_inv,
        key_items=key_items,
        scene_location=scene_loc,
        time_constraint=time_constr,
        embedding_api_key=embedding_api_key,
        embedding_url=embedding_url,
        embedding_interface_format=embedding_interface_format,
        embedding_model_name=embedding_model_name,
        embedding_retrieval_k=embedding_k,
        interface_format=draft_interface_format,
        max_tokens=draft_max_tokens,
        timeout=draft_timeout,
        system_prompt=resolve_global_system_prompt(),  # 从PromptManager读取配置
        num_volumes=num_volumes,  # 新增：传递分卷数量
        total_chapters=total_chapters,  # 新增：传递总章节数
        gui_log_callback=self.safe_log  # 传入回调，显示向量检索详情
    )

    # 处理角色库
    final_prompt = prompt_text
    # 兼容逗号和换行两种分隔符
    char_text = self.char_inv_text.get("0.0", "end").strip()
    role_names = []
    if ',' in char_text:
        # 逗号分隔格式（与单章流程一致）
        role_names = [name.strip() for name in char_text.split(',') if name.strip()]
    else:
        # 换行分隔格式
        role_names = [name.strip() for name in char_text.split("\n") if name.strip()]

    role_lib_path = os.path.join(self.filepath_var.get().strip(), "角色库")
    role_contents = []

    if os.path.exists(role_lib_path):
        for root, dirs, files in os.walk(role_lib_path):
            for file in files:
                if file.endswith(".txt") and os.path.splitext(file)[0] in role_names:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            role_contents.append(f.read().strip())
                    except Exception as e:
                        self.safe_log(f"读取角色文件 {file} 失败: {str(e)}")

    if role_contents:
        role_content_str = "\n".join(role_contents)
        placeholder_variations = [
            "核心人物(可能未指定)：{characters_involved}",
            "核心人物：{characters_involved}",
            "核心人物(可能未指定):{characters_involved}",
            "核心人物:{characters_involved}"
        ]

        for placeholder in placeholder_variations:
            if placeholder in final_prompt:
                final_prompt = final_prompt.replace(
                    placeholder,
                    f"核心人物：\n{role_content_str}"
                )
                break
        else:
            lines = final_prompt.split('\n')
            for idx, line in enumerate(lines):
                if "核心人物" in line and "：" in line:
                    lines[idx] = f"核心人物：\n{role_content_str}"
                    break
            final_prompt = '\n'.join(lines)

    self.update_chapter_progress("提示词构建完成", 0.33)

    # ========== 阶段2: 生成草稿 ==========
    self.safe_log("\n▶ [阶段2/3] 生成章节草稿")
    self.update_chapter_progress("生成草稿中...", 0.33)

    draft_text = generate_chapter_draft(
        api_key=draft_api_key,
        base_url=draft_base_url,
        model_name=draft_model_name,
        filepath=self.filepath_var.get().strip(),
        novel_number=chapter_num,
        word_number=word,
        temperature=draft_temperature,
        user_guidance=user_guidance,
        characters_involved=char_inv,
        key_items=key_items,
        scene_location=scene_loc,
        time_constraint=time_constr,
        embedding_api_key=embedding_api_key,
        embedding_url=embedding_url,
        embedding_interface_format=embedding_interface_format,
        embedding_model_name=embedding_model_name,
        embedding_retrieval_k=embedding_k,
        interface_format=draft_interface_format,
        max_tokens=draft_max_tokens,
        timeout=draft_timeout,
        custom_prompt_text=final_prompt,
        use_global_system_prompt=None,  # 使用PromptManager配置
        num_volumes=self.safe_get_int(self.num_volumes_var, 0),  # 新增：传递分卷参数
        total_chapters=self.safe_get_int(self.num_chapters_var, 0),  # 新增：传递总章节数
        gui_log_callback=self.safe_log  # 传入回调
    )

    # 检查字数并扩写
    chapters_dir = os.path.join(self.filepath_var.get().strip(), "chapters")
    os.makedirs(chapters_dir, exist_ok=True)
    chapter_path = os.path.join(chapters_dir, f"chapter_{chapter_num}.txt")

    if len(draft_text) < 0.7 * min_word and auto_enrich:
        self.safe_log(f"\n⚠️  字数不足 ({len(draft_text)}/{min_word})")
        self.safe_log("   ├─ 启动自动扩写...")
        self.update_chapter_progress("扩写中...", 0.5)

        enriched = enrich_chapter_text(
            chapter_text=draft_text,
            word_number=word,
            api_key=draft_api_key,
            base_url=draft_base_url,
            model_name=draft_model_name,
            temperature=draft_temperature,
            interface_format=draft_interface_format,
            max_tokens=draft_max_tokens,
            timeout=draft_timeout,
            use_global_system_prompt=None  # 使用PromptManager配置
        )
        draft_text = enriched
        self.safe_log(f"   └─ ✅ 扩写完成 (现{len(draft_text)}字)\n")

    # 保存草稿
    clear_file_content(chapter_path)
    save_string_to_txt(draft_text, chapter_path)

    self.update_chapter_progress("草稿完成", 0.66)

    # ========== 阶段3: 定稿章节 ==========
    self.safe_log("\n▶ [阶段3/3] 章节定稿")
    self.update_chapter_progress("定稿中...", 0.66)

    success = finalize_chapter(
        novel_number=chapter_num,
        word_number=word,
        api_key=finalize_api_key,
        base_url=finalize_base_url,
        model_name=finalize_model_name,
        temperature=finalize_temperature,
        filepath=self.filepath_var.get().strip(),
        embedding_api_key=embedding_api_key,
        embedding_url=embedding_url,
        embedding_interface_format=embedding_interface_format,
        embedding_model_name=embedding_model_name,
        interface_format=finalize_interface_format,
        max_tokens=finalize_max_tokens,
        timeout=finalize_timeout,
        use_global_system_prompt=None,  # 使用PromptManager配置
        num_volumes=self.safe_get_int(self.num_volumes_var, 0),  # 新增：传递分卷参数
        total_chapters=self.safe_get_int(self.num_chapters_var, 0),  # 新增：传递总章节数
        gui_log_callback=self.safe_log  # 传入回调
    )

    if success:
        self.update_chapter_progress("完成", 1.0)
        self.safe_log(f"✅ 第 {chapter_num} 章定稿完成")
    else:
        self.safe_log(f"⚠️ 第 {chapter_num} 章定稿失败（章节内容为空）")


def import_knowledge_handler(self):
    selected_file = tk.filedialog.askopenfilename(
        title="选择要导入的知识库文件",
        filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
    )
    if selected_file:
        def task():
            self.disable_button_safe(self.btn_import_knowledge)
            try:
                emb_api_key = self.embedding_api_key_var.get().strip()
                emb_url = self.embedding_url_var.get().strip()
                emb_format = self.embedding_interface_format_var.get().strip()
                emb_model = self.embedding_model_name_var.get().strip()

                # 尝试不同编码读取文件
                content = None
                encodings = ['utf-8', 'gbk', 'gb2312', 'ansi']
                for encoding in encodings:
                    try:
                        with open(selected_file, 'r', encoding=encoding) as f:
                            content = f.read()
                            break
                    except UnicodeDecodeError:
                        continue
                    except Exception as e:
                        self.safe_log(f"读取文件时发生错误: {str(e)}")
                        raise

                if content is None:
                    raise Exception("无法以任何已知编码格式读取文件")

                # 创建临时UTF-8文件
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False, suffix='.txt') as temp:
                    temp.write(content)
                    temp_path = temp.name

                try:
                    self.safe_log(f"开始导入知识库文件: {selected_file}")
                    import_knowledge_file(
                        embedding_api_key=emb_api_key,
                        embedding_url=emb_url,
                        embedding_interface_format=emb_format,
                        embedding_model_name=emb_model,
                        file_path=temp_path,
                        filepath=self.filepath_var.get().strip()
                    )
                    self.safe_log("✅ 知识库文件导入完成。")
                finally:
                    # 清理临时文件
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

            except Exception:
                self.handle_exception("导入知识库时出错")
            finally:
                self.enable_button_safe(self.btn_import_knowledge)

        try:
            thread = threading.Thread(target=task, daemon=True)
            thread.start()
        except Exception as e:
            self.enable_button_safe(self.btn_import_knowledge)
            messagebox.showerror("错误", f"线程启动失败: {str(e)}")

def clear_vectorstore_handler(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return

    first_confirm = messagebox.askyesno("警告", "确定要清空本地向量库吗？此操作不可恢复！")
    if first_confirm:
        second_confirm = messagebox.askyesno("再次确认", "清空向量库后，需要重新定稿所有章节才能使用向量检索功能。\n\n确定继续吗？")
        if second_confirm:
            from novel_generator.vectorstore_utils import clear_vector_store
            from novel_generator.vectorstore_monitor import clear_stats
            try:
                clear_vector_store(filepath)
                clear_stats(filepath)  # 同时清空统计数据
                self.safe_log("✅ 向量库和统计数据已清空。")
            except Exception as e:
                messagebox.showerror("错误", f"清空向量库失败: {str(e)}")

def show_vectorstore_report(self):
    """显示向量库质量报告"""
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先配置保存文件路径。")
        return

    try:
        from novel_generator.vectorstore_monitor import get_usage_report, analyze_quality

        # 生成报告
        report = get_usage_report(filepath)

        # 创建弹窗显示报告
        report_window = ctk.CTkToplevel(self.master)
        report_window.title("向量库质量报告")
        report_window.geometry("800x600")

        # 添加标题
        title_label = ctk.CTkLabel(
            report_window,
            text="向量库使用统计与质量分析",
            font=("Microsoft YaHei", 16, "bold")
        )
        title_label.pack(pady=10)

        # 添加文本框显示报告
        report_text = ctk.CTkTextbox(
            report_window,
            wrap="word",
            font=("Consolas", 11)
        )
        report_text.pack(fill="both", expand=True, padx=20, pady=10)
        report_text.insert("0.0", report)
        report_text.configure(state="disabled")  # 只读

        # 按钮区域
        button_frame = ctk.CTkFrame(report_window)
        button_frame.pack(pady=10)

        # 刷新按钮
        def refresh_report():
            new_report = get_usage_report(filepath)
            report_text.configure(state="normal")
            report_text.delete("0.0", "end")
            report_text.insert("0.0", new_report)
            report_text.configure(state="disabled")

        refresh_btn = ctk.CTkButton(
            button_frame,
            text="刷新报告",
            command=refresh_report,
            font=("Microsoft YaHei", 12)
        )
        refresh_btn.pack(side="left", padx=5)

        # 清空统计按钮
        def clear_stats_confirm():
            if messagebox.askyesno("确认", "确定要清空统计数据吗？\n(不会删除向量库内容)"):
                from novel_generator.vectorstore_monitor import clear_stats
                clear_stats(filepath)
                self.safe_log("✅ 向量库统计数据已清空。")
                refresh_report()

        clear_stats_btn = ctk.CTkButton(
            button_frame,
            text="清空统计",
            command=clear_stats_confirm,
            font=("Microsoft YaHei", 12),
            fg_color="orange"
        )
        clear_stats_btn.pack(side="left", padx=5)

        # 关闭按钮
        close_btn = ctk.CTkButton(
            button_frame,
            text="关闭",
            command=report_window.destroy,
            font=("Microsoft YaHei", 12)
        )
        close_btn.pack(side="left", padx=5)

        report_window.transient(self.master)
        report_window.focus()

    except Exception as e:
        messagebox.showerror("错误", f"生成报告失败: {str(e)}\n\n{traceback.format_exc()}")

def show_plot_arcs_ui(self):
    filepath = self.filepath_var.get().strip()
    if not filepath:
        messagebox.showwarning("警告", "请先在主Tab中设置保存文件路径")
        return

    plot_arcs_file = os.path.join(filepath, "plot_arcs.txt")
    if not os.path.exists(plot_arcs_file):
        messagebox.showinfo("剧情要点", "当前还未生成任何剧情要点或冲突记录。")
        return

    arcs_text = read_file(plot_arcs_file).strip()
    if not arcs_text:
        arcs_text = "当前没有记录的剧情要点或冲突。"

    top = ctk.CTkToplevel(self.master)
    top.title("剧情要点/未解决冲突")
    top.geometry("600x400")
    text_area = ctk.CTkTextbox(top, wrap="word", font=("Microsoft YaHei", 12))
    text_area.pack(fill="both", expand=True, padx=10, pady=10)
    text_area.insert("0.0", arcs_text)
    text_area.configure(state="disabled")
