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

    def _create_default_config(self) -> dict:
        """创建默认配置（所有模块启用）"""
        return {
            "_version": "1.0",
            "modules": {
                "architecture": {
                    "core_seed": {"enabled": True, "required": True},
                    "character_dynamics": {"enabled": True, "required": False},
                    "world_building": {"enabled": True, "required": False},
                    "plot_architecture": {"enabled": True, "required": False},
                    "volume_breakdown": {"enabled": True, "required": False}  # 修复：从blueprint移到architecture
                },
                "blueprint": {
                    "chapter_blueprint": {"enabled": True, "required": True},
                    "chunked_blueprint": {"enabled": True, "required": True}
                },
                "chapter": {
                    "first_chapter": {"enabled": True, "required": True},
                    "next_chapter": {"enabled": True, "required": True},
                    "chapter_summary": {"enabled": True, "required": False}
                },
                "finalization": {
                    "summary_update": {"enabled": True, "required": False},
                    "character_state_update": {"enabled": True, "required": False},
                    "volume_summary": {"enabled": True, "required": False},
                    "plot_arcs_update": {"enabled": True, "required": False},  # 新增
                    "plot_arcs_distill": {"enabled": True, "required": False},  # 新增
                    "plot_arcs_compress": {"enabled": True, "required": False}  # 新增
                },
                "helper": {
                    "knowledge_search": {"enabled": True, "required": False},
                    "knowledge_filter": {"enabled": True, "required": False},
                    "create_character_state": {"enabled": True, "required": False},
                    "global_system": {"enabled": False, "required": False}
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
                plot_arcs_compress_prompt  # 新增：剧情要点压缩
            )
            return {
                "core_seed_prompt": core_seed_prompt,
                "character_dynamics_prompt": character_dynamics_prompt,
                "world_building_prompt": world_building_prompt,
                "plot_architecture_prompt": plot_architecture_prompt,
                "chapter_blueprint_prompt": chapter_blueprint_prompt,
                "chunked_chapter_blueprint_prompt": chunked_chapter_blueprint_prompt,
                "volume_breakdown_prompt": volume_breakdown_prompt,
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
            ("blueprint", "chapter_blueprint"): "chapter_blueprint_prompt",
            ("blueprint", "chunked_blueprint"): "chunked_chapter_blueprint_prompt",
            ("chapter", "first_chapter"): "first_chapter_draft_prompt",
            ("chapter", "next_chapter"): "next_chapter_draft_prompt",
            ("chapter", "chapter_summary"): "summarize_recent_chapters_prompt",
            ("finalization", "summary_update"): "summary_prompt",
            ("finalization", "character_state_update"): "update_character_state_prompt",
            ("finalization", "volume_summary"): "volume_summary_prompt",
            ("finalization", "plot_arcs_update"): "plot_arcs_update_prompt",  # 新增
            ("finalization", "plot_arcs_distill"): "plot_arcs_distill_prompt",  # 新增
            ("finalization", "plot_arcs_compress"): "plot_arcs_compress_prompt",  # 新增
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


