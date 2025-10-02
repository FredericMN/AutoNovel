# ui/prompt_manager_builder.py
# -*- coding: utf-8 -*-
"""
构建提示词管理页签
"""
from ui.prompt_manager_tab import PromptManagerTab

def build_prompt_manager_tab(app):
    """
    构建提示词管理页签

    Args:
        app: 主窗口实例
    """
    # 添加页签
    tab = app.tabview.add("提示词管理")

    # 创建提示词管理组件
    prompt_manager = PromptManagerTab(tab)
    prompt_manager.pack(fill="both", expand=True, padx=0, pady=0)

    # 保存引用
    app.prompt_manager_tab = prompt_manager

