# prompt_manager_helper.py
# -*- coding: utf-8 -*-
"""
PromptManager 辅助函数
提供统一的初始化和获取提示词逻辑，带完整的异常保护和 fallback 机制
"""
import logging
from typing import Optional


def get_prompt_manager():
    """
    安全地初始化 PromptManager，失败时返回 Fallback 对象

    Returns:
        PromptManager 实例或 FallbackPromptManager 实例
    """
    try:
        from .prompt_manager import PromptManager
        return PromptManager()
    except Exception as e:
        logging.error(f"Failed to initialize PromptManager: {e}")

        # 创建 Fallback 对象
        class FallbackPromptManager:
            def is_module_enabled(self, category, name):
                return True  # 默认全部启用
            def get_prompt(self, category, name):
                return None  # 返回 None，触发调用方使用默认常量

        return FallbackPromptManager()


def get_prompt_with_fallback(
    category: str,
    name: str,
    fallback_prompt: str,
    pm=None,
    warn_on_fallback: bool = True
) -> str:
    """
    从 PromptManager 获取提示词，失败时使用 fallback

    Args:
        category: 提示词分类 (architecture/blueprint/chapter/finalization/helper)
        name: 提示词名称
        fallback_prompt: 默认提示词常量 (来自 prompt_definitions.py)
        pm: PromptManager 实例 (可选，如为 None 则自动创建)
        warn_on_fallback: 使用 fallback 时是否记录警告

    Returns:
        提示词字符串

    Example:
        from core.prompting.prompt_definitions import chapter_blueprint_prompt
        pm = get_prompt_manager()
        prompt = get_prompt_with_fallback(
            "blueprint", "chapter_blueprint",
            chapter_blueprint_prompt,
            pm=pm
        )
    """
    # 如果没有传入 pm，自动创建
    if pm is None:
        pm = get_prompt_manager()

    # 尝试从 PromptManager 获取
    prompt_template = pm.get_prompt(category, name)

    # 如果获取失败或为空，使用 fallback
    if not prompt_template:
        if warn_on_fallback:
            logging.warning(f"Prompt {category}.{name} not found or empty, using fallback")
        return fallback_prompt

    return prompt_template


# 便捷函数：针对各个模块的快捷方式

def get_architecture_prompt(name: str, fallback_prompt: str, pm=None) -> str:
    """获取架构生成提示词"""
    return get_prompt_with_fallback("architecture", name, fallback_prompt, pm)


def get_blueprint_prompt(name: str, fallback_prompt: str, pm=None) -> str:
    """获取蓝图生成提示词"""
    return get_prompt_with_fallback("blueprint", name, fallback_prompt, pm)


def get_chapter_prompt(name: str, fallback_prompt: str, pm=None) -> str:
    """获取章节生成提示词"""
    return get_prompt_with_fallback("chapter", name, fallback_prompt, pm)


def get_finalization_prompt(name: str, fallback_prompt: str, pm=None) -> str:
    """获取定稿提示词"""
    return get_prompt_with_fallback("finalization", name, fallback_prompt, pm)


def get_helper_prompt(name: str, fallback_prompt: str, pm=None) -> str:
    """获取辅助功能提示词"""
    return get_prompt_with_fallback("helper", name, fallback_prompt, pm)



