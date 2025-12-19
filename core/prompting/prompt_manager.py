# prompt_manager.py
# -*- coding: utf-8 -*-
"""
提示词管理器
负责加载、保存、管理所有提示词模块
"""
import json
import os
import logging
from typing import Dict, Optional

class PromptManager:
    """提示词管理器"""

    def __init__(self, config_path="prompts_config.json", custom_dir="custom_prompts"):
        self.config_path = config_path
        self.custom_dir = custom_dir
        self.config = self.load_config()
        self.default_prompts = self._load_default_prompts()

        # 确保自定义提示词目录存在
        os.makedirs(self.custom_dir, exist_ok=True)

    def load_config(self) -> dict:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 验证配置格式
                if self._validate_config(config):
                    # 迁移：补全缺失的模块配置
                    config = self._migrate_config(config)
                    return config
                else:
                    logging.warning("Config validation failed, creating backup and using default")
                    self._backup_config()
                    return self._create_default_config()

            except json.JSONDecodeError as e:
                logging.error(f"JSON parse error in prompts_config.json: {e}")
                self._backup_config()
                return self._create_default_config()
            except Exception as e:
                logging.error(f"Failed to load prompts_config.json: {e}")
                self._backup_config()
                return self._create_default_config()
        return self._create_default_config()

    def _validate_config(self, config: dict) -> bool:
        """验证配置文件格式"""
        try:
            # 检查必需字段
            if "modules" not in config:
                logging.error("Config missing 'modules' field")
                return False

            # 检查每个模块的必需字段
            for category, modules in config["modules"].items():
                for name, module_data in modules.items():
                    required_fields = ["enabled", "required"]
                    for field in required_fields:
                        if field not in module_data:
                            logging.error(f"Module {category}.{name} missing field '{field}'")
                            return False

            return True
        except Exception as e:
            logging.error(f"Config validation error: {e}")
            return False

    def _backup_config(self):
        """备份配置文件"""
        if os.path.exists(self.config_path):
            try:
                import shutil
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"{self.config_path}.backup_{timestamp}"
                shutil.copy2(self.config_path, backup_path)
                logging.info(f"Config backed up to: {backup_path}")
                print(f"⚠️ 配置文件格式错误，已备份至: {backup_path}")
            except Exception as e:
                logging.error(f"Failed to backup config: {e}")

    def _migrate_config(self, config: dict) -> dict:
        """
        配置迁移：补全缺失的模块和字段，并更新过期的变量清单

        当用户已有 prompts_config.json 但缺少新版本模块或字段时，
        自动从默认配置中补充，确保新功能可用。

        迁移策略：
        1. 补充缺失的分类（category）
        2. 补充缺失的模块（module）
        3. 补充已存在模块的缺失字段（file, display_name, variables, dependencies, description）
        4. 🆕 强制更新 variables 字段（确保与最新模板同步）

        Args:
            config: 用户现有配置

        Returns:
            补全后的配置
        """
        default_config = self._create_default_config()
        migrated = False

        # 必需字段列表（这些字段必须存在于每个模块中）
        required_fields = ["enabled", "required", "file", "display_name", "description", "variables", "dependencies"]

        # 需要强制更新的字段（即使已存在也覆盖，确保与最新版本同步）
        force_update_fields = ["variables"]

        # 遍历默认配置中的所有模块
        for category, modules in default_config["modules"].items():
            # 如果用户配置中缺少该分类，整个添加
            if category not in config["modules"]:
                config["modules"][category] = modules
                logging.info(f"Config migration: added category '{category}'")
                migrated = True
                continue

            # 遍历该分类下的所有模块
            for name, default_module_data in modules.items():
                if name not in config["modules"][category]:
                    # 模块不存在，整个添加
                    config["modules"][category][name] = default_module_data
                    logging.info(f"Config migration: added module '{category}.{name}'")
                    migrated = True
                else:
                    # 模块已存在，检查并补充/更新字段
                    existing_module = config["modules"][category][name]
                    for field in required_fields:
                        if field not in existing_module:
                            # 字段缺失，添加
                            existing_module[field] = default_module_data.get(field, [] if field in ["variables", "dependencies"] else "")
                            logging.info(f"Config migration: added field '{field}' to module '{category}.{name}'")
                            migrated = True
                        elif field in force_update_fields:
                            # 字段存在但需要强制更新（variables）
                            old_value = existing_module[field]
                            new_value = default_module_data.get(field, [])
                            if old_value != new_value:
                                existing_module[field] = new_value
                                logging.info(f"Config migration: updated field '{field}' in module '{category}.{name}' (was: {len(old_value)} items, now: {len(new_value)} items)")
                                migrated = True

        # 如果有迁移，保存更新后的配置
        if migrated:
            try:
                self._save_config_dict(config)
                logging.info("Config migration completed and saved")
            except Exception as e:
                logging.warning(f"Failed to save migrated config: {e}")

        return config

    def _save_config_dict(self, config: dict):
        """保存配置字典到文件（内部使用）"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Failed to save config: {e}")
            raise

    def _create_default_config(self) -> dict:
        """
        创建默认配置（与 prompts_config.json 完全一致）

        此配置用于：
        1. 当配置文件不存在时创建新配置
        2. 迁移时补充缺失的模块和字段

        注意：此方法的内容必须与 prompts_config.json 保持同步
        """
        return {
            "_version": "1.0",
            "_description": "提示词模块配置文件 - Prompt Module Configuration",
            "_last_modified": "2025-10-01",
            "_note": "enabled=true表示启用，required=true表示必需模块不可禁用，dependencies列出依赖的其他模块",
            "modules": {
                "architecture": {
                    "core_seed": {
                        "enabled": True,
                        "required": True,
                        "display_name": "核心种子生成",
                        "description": "生成小说的核心主题、类型和冲突",
                        "file": "custom_prompts/core_seed_prompt.txt",
                        "dependencies": [],
                        "variables": ["topic", "genre", "number_of_chapters", "word_number", "user_guidance"]
                    },
                    "character_dynamics": {
                        "enabled": True,
                        "required": False,
                        "display_name": "角色动力学",
                        "description": "角色设定、性格、关系网络",
                        "file": "custom_prompts/character_dynamics_prompt.txt",
                        "dependencies": [],
                        "variables": ["core_seed", "user_guidance"]
                    },
                    "world_building": {
                        "enabled": True,
                        "required": False,
                        "display_name": "世界观构建",
                        "description": "世界观、背景设定、规则体系",
                        "file": "custom_prompts/world_building_prompt.txt",
                        "dependencies": [],
                        "variables": ["core_seed", "user_guidance"]
                    },
                    "plot_architecture": {
                        "enabled": True,
                        "required": False,
                        "display_name": "三幕式情节",
                        "description": "情节架构（起承转合）",
                        "file": "custom_prompts/plot_architecture_prompt.txt",
                        "dependencies": ["character_dynamics", "world_building"],
                        "variables": ["core_seed", "character_dynamics", "world_building", "user_guidance", "number_of_chapters", "num_volumes"]
                    },
                    "volume_breakdown": {
                        "enabled": True,
                        "required": False,
                        "display_name": "分卷架构",
                        "description": "分卷小说的卷架构规划",
                        "file": "custom_prompts/volume_breakdown_prompt.txt",
                        "dependencies": [],
                        "variables": ["novel_architecture", "num_volumes", "num_chapters", "volume_format_examples"]
                    },
                    "user_concept_to_core_seed": {
                        "enabled": True,
                        "required": False,
                        "display_name": "构思提炼核心种子",
                        "description": "【构思模式】从用户已有故事构思中提炼核心种子",
                        "file": "custom_prompts/user_concept_to_core_seed_prompt.txt",
                        "dependencies": [],
                        "variables": ["user_concept", "genre", "number_of_chapters", "word_number", "user_guidance"]
                    },
                    "concept_character_dynamics": {
                        "enabled": True,
                        "required": False,
                        "display_name": "构思角色动力学",
                        "description": "【构思模式】基于用户构思设计角色，优先采用用户已有角色设定",
                        "file": "custom_prompts/concept_character_dynamics_prompt.txt",
                        "dependencies": ["user_concept_to_core_seed"],
                        "variables": ["user_concept", "core_seed", "user_guidance"]
                    },
                    "concept_world_building": {
                        "enabled": True,
                        "required": False,
                        "display_name": "构思世界观构建",
                        "description": "【构思模式】基于用户构思构建世界观，优先采用用户已有设定",
                        "file": "custom_prompts/concept_world_building_prompt.txt",
                        "dependencies": ["user_concept_to_core_seed"],
                        "variables": ["user_concept", "core_seed", "user_guidance"]
                    }
                },
                "blueprint": {
                    "chapter_blueprint": {
                        "enabled": True,
                        "required": True,
                        "display_name": "章节蓝图",
                        "description": "生成所有章节的标题和大纲",
                        "file": "custom_prompts/chapter_blueprint_prompt.txt",
                        "dependencies": [],
                        "variables": ["novel_architecture", "number_of_chapters", "user_guidance"]
                    },
                    "chunked_blueprint": {
                        "enabled": True,
                        "required": True,
                        "display_name": "分块蓝图生成",
                        "description": "分块生成大量章节的蓝图",
                        "file": "custom_prompts/chunked_chapter_blueprint_prompt.txt",
                        "dependencies": [],
                        "variables": ["novel_architecture", "chapter_list", "number_of_chapters", "n", "m", "user_guidance"]
                    },
                    "volume_chapter_blueprint": {
                        "enabled": True,
                        "required": False,
                        "display_name": "分卷章节蓝图",
                        "description": "分卷模式下生成每一卷的章节蓝图",
                        "file": "custom_prompts/volume_chapter_blueprint_prompt.txt",
                        "dependencies": [],
                        "variables": ["novel_architecture", "volume_architecture", "volume_number", "volume_start", "volume_end", "volume_total_chapters", "volume_chapter_count", "volume_original_start", "previous_volumes_summary", "resume_mode_notice", "user_guidance"]
                    }
                },
                "chapter": {
                    "first_chapter": {
                        "enabled": True,
                        "required": True,
                        "display_name": "第一章草稿",
                        "description": "生成第一章的草稿内容",
                        "file": "custom_prompts/first_chapter_draft_prompt.txt",
                        "dependencies": [],
                        "variables": ["volume_display", "volume_architecture", "unresolved_plot_arcs", "novel_number", "chapter_title", "chapter_role", "chapter_purpose", "suspense_level", "foreshadowing", "plot_twist_level", "word_number", "volume_position", "chapter_summary", "characters_involved", "key_items", "scene_location", "time_constraint", "user_guidance", "novel_setting"]
                    },
                    "next_chapter": {
                        "enabled": True,
                        "required": True,
                        "display_name": "后续章节草稿",
                        "description": "生成第二章及以后的草稿内容",
                        "file": "custom_prompts/next_chapter_draft_prompt.txt",
                        "dependencies": [],
                        "variables": ["global_summary", "volume_info", "volume_architecture", "unresolved_plot_arcs", "previous_chapter_excerpt", "character_state", "short_summary", "current_volume_display", "novel_number", "chapter_title", "chapter_role", "chapter_purpose", "suspense_level", "foreshadowing", "plot_twist_level", "word_number", "volume_position", "chapter_summary", "characters_involved", "key_items", "scene_location", "time_constraint", "user_guidance", "next_volume_display", "next_chapter_number", "next_chapter_title", "next_chapter_role", "next_chapter_purpose", "next_chapter_suspense_level", "next_chapter_foreshadowing", "next_chapter_plot_twist_level", "next_chapter_summary", "filtered_context"]
                    },
                    "critique": {
                        "enabled": False,
                        "required": False,
                        "display_name": "批评家审阅【Plan C】",
                        "description": "【Plan C - 默认关闭】对初稿进行批评性分析，指出逻辑和文笔问题。⚠️ 启用后每章增加2次API调用，成本较高",
                        "file": "custom_prompts/critique_prompt.txt",
                        "dependencies": [],
                        "variables": ["novel_number", "chapter_title", "chapter_text", "short_summary", "previous_chapter_excerpt"]
                    },
                    "refine": {
                        "enabled": False,
                        "required": False,
                        "display_name": "作家重写【Plan C】",
                        "description": "【Plan C - 默认关闭】根据批评意见重写章节，需与批评家模块同时启用才能生效",
                        "file": "custom_prompts/refine_prompt.txt",
                        "dependencies": ["critique"],
                        "variables": ["critique", "draft_text", "word_number", "short_summary", "previous_chapter_excerpt"]
                    },
                    "single_chapter_summary": {
                        "enabled": True,
                        "required": False,
                        "display_name": "单章摘要缓存【Plan B】",
                        "description": "【Plan B】定稿时生成单章摘要缓存，后续章节优先读取摘要而非全文，节省Token",
                        "file": "custom_prompts/single_chapter_summary_prompt.txt",
                        "dependencies": [],
                        "variables": ["novel_number", "chapter_title", "chapter_text"]
                    },
                    "chapter_summary": {
                        "enabled": True,
                        "required": False,
                        "display_name": "多章合并摘要",
                        "description": "生成最近几章的合并摘要（旧版逻辑）",
                        "file": "custom_prompts/summarize_recent_chapters_prompt.txt",
                        "dependencies": [],
                        "variables": ["combined_text", "novel_number", "chapter_title", "chapter_role", "chapter_purpose", "suspense_level", "foreshadowing", "plot_twist_level", "chapter_summary", "next_chapter_number", "next_chapter_title", "next_chapter_role", "next_chapter_purpose", "next_chapter_suspense_level", "next_chapter_foreshadowing", "next_chapter_plot_twist_level", "next_chapter_summary"]
                    }
                },
                "finalization": {
                    "summary_update": {
                        "enabled": True,
                        "required": False,
                        "display_name": "前文摘要更新",
                        "description": "定稿时更新全局摘要",
                        "file": "custom_prompts/summary_prompt.txt",
                        "dependencies": [],
                        "variables": ["chapter_text", "global_summary"]
                    },
                    "character_state_update": {
                        "enabled": True,
                        "required": False,
                        "display_name": "角色状态更新",
                        "description": "定稿时更新角色状态表",
                        "file": "custom_prompts/update_character_state_prompt.txt",
                        "dependencies": [],
                        "variables": ["chapter_text", "old_state"]
                    },
                    "volume_summary": {
                        "enabled": True,
                        "required": False,
                        "display_name": "卷总结生成",
                        "description": "生成每卷的总结",
                        "file": "custom_prompts/volume_summary_prompt.txt",
                        "dependencies": [],
                        "variables": ["volume_number", "volume_start", "volume_end"]
                    },
                    "plot_arcs_update": {
                        "enabled": True,
                        "required": False,
                        "display_name": "剧情要点更新",
                        "description": "记录未解决伏笔，按ABC级分类（步骤2.5/3）",
                        "file": "custom_prompts/plot_arcs_update_prompt.txt",
                        "dependencies": [],
                        "variables": ["chapter_text", "old_plot_arcs"]
                    },
                    "plot_arcs_distill": {
                        "enabled": True,
                        "required": False,
                        "display_name": "伏笔提炼（精简版）",
                        "description": "提炼核心伏笔融入摘要：A级5条+B级3条（步骤2.8/3）",
                        "file": "custom_prompts/plot_arcs_distill_prompt.txt",
                        "dependencies": ["plot_arcs_update"],
                        "variables": ["plot_arcs_text"]
                    },
                    "plot_arcs_compress": {
                        "enabled": True,
                        "required": False,
                        "display_name": "伏笔二次压缩",
                        "description": "当精简版超过200字时触发二次压缩（步骤2.8/3）",
                        "file": "custom_prompts/plot_arcs_compress_prompt.txt",
                        "dependencies": ["plot_arcs_distill"],
                        "variables": ["distilled_arcs"]
                    },
                    "plot_arcs_compress_auto": {
                        "enabled": True,
                        "required": False,
                        "display_name": "智能自动压缩",
                        "description": "周期性压缩详细版：A级≤30条、B级≤10条、C级≤3条（步骤2.6/3，每10章触发）",
                        "file": "custom_prompts/plot_arcs_compress_auto.txt",
                        "dependencies": ["plot_arcs_update"],
                        "variables": ["classified_plot_arcs", "current_chapter", "unresolved_count", "resolved_count"]
                    }
                },
                "helper": {
                    "knowledge_search": {
                        "enabled": True,
                        "required": False,
                        "display_name": "知识库搜索",
                        "description": "从知识库中搜索相关内容",
                        "file": "custom_prompts/knowledge_search_prompt.txt",
                        "dependencies": [],
                        "variables": ["chapter_number", "chapter_title", "characters_involved", "key_items", "scene_location", "chapter_role", "chapter_purpose", "foreshadowing", "short_summary", "user_guidance", "time_constraint"]
                    },
                    "knowledge_filter": {
                        "enabled": True,
                        "required": False,
                        "display_name": "知识库过滤",
                        "description": "过滤知识库搜索结果",
                        "file": "custom_prompts/knowledge_filter_prompt.txt",
                        "dependencies": [],
                        "variables": ["retrieved_texts", "chapter_info"]
                    },
                    "create_character_state": {
                        "enabled": True,
                        "required": False,
                        "display_name": "初始角色状态",
                        "description": "创建初始角色状态表",
                        "file": "custom_prompts/create_character_state_prompt.txt",
                        "dependencies": ["character_dynamics"],
                        "variables": ["character_dynamics"]
                    },
                    "global_system": {
                        "enabled": False,
                        "required": False,
                        "display_name": "全局System Prompt",
                        "description": "全局系统提示词（所有LLM调用都会注入）",
                        "file": "custom_prompts/system_prompt.txt",
                        "dependencies": [],
                        "variables": []
                    }
                }
            }
        }

    def _load_default_prompts(self) -> dict:
        """从 prompt_definitions.py 加载默认提示词"""
        try:
            from .prompt_definitions import (
                core_seed_prompt,
                character_dynamics_prompt,
                world_building_prompt,
                plot_architecture_prompt,
                chapter_blueprint_prompt,
                chunked_chapter_blueprint_prompt,
                volume_breakdown_prompt,
                volume_chapter_blueprint_prompt,  # 🆕 新增：分卷章节蓝图
                first_chapter_draft_prompt,
                next_chapter_draft_prompt,
                summarize_recent_chapters_prompt,
                summary_prompt,
                update_character_state_prompt,
                volume_summary_prompt,
                knowledge_search_prompt,
                knowledge_filter_prompt,
                create_character_state_prompt,
                plot_arcs_update_prompt,  # 新增：剧情要点更新
                plot_arcs_distill_prompt,  # 新增：剧情要点提炼
                plot_arcs_compress_prompt,  # 新增：剧情要点压缩
                plot_arcs_compress_auto_prompt,  # 🆕 剧情要点自动压缩
                single_chapter_summary_prompt,  # 🆕 单章摘要
                chapter_critique_prompt,  # 🆕 批评家
                chapter_refine_prompt,  # 🆕 作家重写
                # 构思模式专用提示词
                user_concept_to_core_seed_prompt,
                concept_character_dynamics_prompt,
                concept_world_building_prompt
            )
            return {
                "core_seed_prompt": core_seed_prompt,
                "character_dynamics_prompt": character_dynamics_prompt,
                "world_building_prompt": world_building_prompt,
                "plot_architecture_prompt": plot_architecture_prompt,
                "chapter_blueprint_prompt": chapter_blueprint_prompt,
                "chunked_chapter_blueprint_prompt": chunked_chapter_blueprint_prompt,
                "volume_breakdown_prompt": volume_breakdown_prompt,
                "volume_chapter_blueprint_prompt": volume_chapter_blueprint_prompt,  # 🆕 新增
                "first_chapter_draft_prompt": first_chapter_draft_prompt,
                "next_chapter_draft_prompt": next_chapter_draft_prompt,
                "summarize_recent_chapters_prompt": summarize_recent_chapters_prompt,
                "summary_prompt": summary_prompt,
                "update_character_state_prompt": update_character_state_prompt,
                "volume_summary_prompt": volume_summary_prompt,
                "knowledge_search_prompt": knowledge_search_prompt,
                "knowledge_filter_prompt": knowledge_filter_prompt,
                "create_character_state_prompt": create_character_state_prompt,
                "plot_arcs_update_prompt": plot_arcs_update_prompt,  # 新增
                "plot_arcs_distill_prompt": plot_arcs_distill_prompt,  # 新增
                "plot_arcs_compress_prompt": plot_arcs_compress_prompt,  # 新增
                "plot_arcs_compress_auto_prompt": plot_arcs_compress_auto_prompt,  # 🆕 新增
                "single_chapter_summary_prompt": single_chapter_summary_prompt,  # 🆕 新增
                "chapter_critique_prompt": chapter_critique_prompt,  # 🆕 新增
                "chapter_refine_prompt": chapter_refine_prompt,  # 🆕 新增
                # 构思模式专用
                "user_concept_to_core_seed_prompt": user_concept_to_core_seed_prompt,
                "concept_character_dynamics_prompt": concept_character_dynamics_prompt,
                "concept_world_building_prompt": concept_world_building_prompt,
                "system_prompt": ""  # 空字符串作为默认值
            }
        except ImportError as e:
            logging.error(f"Failed to import prompts from prompt_definitions.py: {e}")
            return {}

    def is_module_enabled(self, category: str, name: str) -> bool:
        """检查模块是否启用"""
        try:
            return self.config["modules"][category][name]["enabled"]
        except KeyError:
            logging.warning(f"Module {category}.{name} not found in config")
            return True  # 默认启用

    def get_prompt(self, category: str, name: str) -> Optional[str]:
        """获取提示词（优先自定义，否则默认）"""
        try:
            module = self.config["modules"][category][name]
            file_path = module["file"]

            # 尝试读取自定义文件
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        return content

            # 否则返回默认值
            prompt_key = self._get_prompt_key(category, name)
            return self.default_prompts.get(prompt_key, "")

        except Exception as e:
            logging.error(f"Failed to get prompt {category}.{name}: {e}")
            return None

    def save_custom_prompt(self, category: str, name: str, content: str):
        """保存自定义提示词到文件"""
        try:
            module = self.config["modules"][category][name]
            file_path = module["file"]

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logging.info(f"Saved custom prompt: {category}.{name}")
        except Exception as e:
            logging.error(f"Failed to save prompt {category}.{name}: {e}")
            raise

    def toggle_module(self, category: str, name: str, enabled: bool):
        """切换模块启用状态"""
        try:
            module = self.config["modules"][category][name]
            if module["required"] and not enabled:
                raise ValueError(f"必需模块 {module.get('display_name', name)} 不能禁用")

            # 检查依赖关系
            if not enabled:
                # 禁用模块时，检查是否有其他模块依赖它
                dependent_modules = self._find_dependent_modules(category, name)
                if dependent_modules:
                    dep_names = [f"{m['display_name']}" for m in dependent_modules]
                    raise ValueError(
                        f"无法禁用 {module.get('display_name', name)}\\n\\n"
                        f"以下模块依赖它：\\n" + "\\n".join([f"• {n}" for n in dep_names]) +
                        f"\\n\\n请先禁用这些模块，或保持启用状态。"
                    )

            module["enabled"] = enabled
            self._save_config()
            logging.info(f"Toggled module {category}.{name}: {enabled}")
        except Exception as e:
            logging.error(f"Failed to toggle module {category}.{name}: {e}")
            raise

    def _find_dependent_modules(self, category: str, name: str) -> list:
        """查找依赖指定模块的其他模块"""
        dependent = []
        all_modules = self.config.get("modules", {})

        for cat, modules in all_modules.items():
            for mod_name, mod_info in modules.items():
                # 跳过自己
                if cat == category and mod_name == name:
                    continue

                # 检查是否启用且依赖当前模块
                if mod_info.get("enabled", False):
                    deps = mod_info.get("dependencies", [])
                    if name in deps:
                        dependent.append({
                            "category": cat,
                            "name": mod_name,
                            "display_name": mod_info.get("display_name", mod_name)
                        })

        return dependent

    def reset_to_default(self, category: str, name: str):
        """重置为默认提示词"""
        try:
            module = self.config["modules"][category][name]
            file_path = module["file"]

            # 删除自定义文件
            if os.path.exists(file_path):
                os.remove(file_path)

            logging.info(f"Reset prompt to default: {category}.{name}")
        except Exception as e:
            logging.error(f"Failed to reset prompt {category}.{name}: {e}")
            raise

    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Failed to save config: {e}")
            raise

    def _get_prompt_key(self, category: str, name: str) -> str:
        """根据category和name获取prompt_key"""
        # 映射关系
        mapping = {
            ("architecture", "core_seed"): "core_seed_prompt",
            ("architecture", "character_dynamics"): "character_dynamics_prompt",
            ("architecture", "world_building"): "world_building_prompt",
            ("architecture", "plot_architecture"): "plot_architecture_prompt",
            ("architecture", "volume_breakdown"): "volume_breakdown_prompt",
            # 构思模式专用
            ("architecture", "user_concept_to_core_seed"): "user_concept_to_core_seed_prompt",
            ("architecture", "concept_character_dynamics"): "concept_character_dynamics_prompt",
            ("architecture", "concept_world_building"): "concept_world_building_prompt",
            ("blueprint", "chapter_blueprint"): "chapter_blueprint_prompt",
            ("blueprint", "chunked_blueprint"): "chunked_chapter_blueprint_prompt",
            ("blueprint", "volume_chapter_blueprint"): "volume_chapter_blueprint_prompt",  # 新增：分卷章节蓝图
            ("chapter", "first_chapter"): "first_chapter_draft_prompt",
            ("chapter", "next_chapter"): "next_chapter_draft_prompt",
            ("chapter", "chapter_summary"): "summarize_recent_chapters_prompt",
            ("chapter", "single_chapter_summary"): "single_chapter_summary_prompt",  # 🆕 Plan B
            ("chapter", "critique"): "chapter_critique_prompt",  # 🆕 Plan C
            ("chapter", "refine"): "chapter_refine_prompt",  # 🆕 Plan C
            ("finalization", "summary_update"): "summary_prompt",
            ("finalization", "character_state_update"): "update_character_state_prompt",
            ("finalization", "volume_summary"): "volume_summary_prompt",
            ("finalization", "plot_arcs_update"): "plot_arcs_update_prompt",  # 新增
            ("finalization", "plot_arcs_distill"): "plot_arcs_distill_prompt",  # 新增
            ("finalization", "plot_arcs_compress"): "plot_arcs_compress_prompt",  # 新增
            ("finalization", "plot_arcs_compress_auto"): "plot_arcs_compress_auto_prompt",  # 🆕 新增
            ("helper", "knowledge_search"): "knowledge_search_prompt",
            ("helper", "knowledge_filter"): "knowledge_filter_prompt",
            ("helper", "create_character_state"): "create_character_state_prompt",
            ("helper", "global_system"): "system_prompt",
        }
        return mapping.get((category, name), "")

    def get_all_modules(self) -> Dict[str, Dict[str, dict]]:
        """获取所有模块的配置信息"""
        return self.config.get("modules", {})

    def get_module_info(self, category: str, name: str) -> Optional[dict]:
        """获取指定模块的完整信息"""
        try:
            return self.config["modules"][category][name]
        except KeyError:
            logging.warning(f"Module {category}.{name} not found")
            return None


