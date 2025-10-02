#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
为 prompts_config.json 批量添加 dependencies 字段
"""
import json
import sys
import io

# 修复Windows控制台编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 读取配置
with open('prompts_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 定义依赖关系
dependencies_map = {
    # architecture 分类
    ("architecture", "core_seed"): [],
    ("architecture", "character_dynamics"): [],
    ("architecture", "world_building"): [],
    ("architecture", "plot_architecture"): ["character_dynamics", "world_building"],
    ("architecture", "volume_breakdown"): [],

    # blueprint 分类
    ("blueprint", "chapter_blueprint"): [],
    ("blueprint", "chunked_blueprint"): [],

    # chapter 分类
    ("chapter", "first_chapter"): [],
    ("chapter", "next_chapter"): [],
    ("chapter", "chapter_summary"): [],

    # finalization 分类
    ("finalization", "summary_update"): [],
    ("finalization", "character_state_update"): [],
    ("finalization", "volume_summary"): [],

    # helper 分类
    ("helper", "knowledge_search"): [],
    ("helper", "knowledge_filter"): [],
    ("helper", "create_character_state"): ["character_dynamics"],
    ("helper", "global_system"): []
}

# 添加 dependencies 字段
for category, modules in config['modules'].items():
    for module_name, module_data in modules.items():
        key = (category, module_name)
        if key in dependencies_map:
            if 'dependencies' not in module_data:
                module_data['dependencies'] = dependencies_map[key]
                print(f"✓ Added dependencies for {category}.{module_name}: {dependencies_map[key]}")
        else:
            print(f"⚠ Unknown module: {category}.{module_name}")

# 保存配置
with open('prompts_config.json', 'w', encoding='utf-8') as f:
    json.dump(config, f, ensure_ascii=False, indent=2)

print("\n✅ Dependencies added successfully!")

