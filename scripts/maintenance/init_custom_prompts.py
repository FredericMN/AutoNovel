# init_custom_prompts.py
# -*- coding: utf-8 -*-
"""
初始化自定义提示词文件
从 core.prompting.prompt_definitions 导出所有默认提示词到 custom_prompts/ 目录
"""
import os
import logging

# 导入所有提示词
from core.prompting.prompt_definitions import (
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
    create_character_state_prompt
)

# 提示词映射表
PROMPT_MAPPING = {
    "custom_prompts/core_seed_prompt.txt": core_seed_prompt,
    "custom_prompts/character_dynamics_prompt.txt": character_dynamics_prompt,
    "custom_prompts/world_building_prompt.txt": world_building_prompt,
    "custom_prompts/plot_architecture_prompt.txt": plot_architecture_prompt,
    "custom_prompts/chapter_blueprint_prompt.txt": chapter_blueprint_prompt,
    "custom_prompts/chunked_chapter_blueprint_prompt.txt": chunked_chapter_blueprint_prompt,
    "custom_prompts/volume_breakdown_prompt.txt": volume_breakdown_prompt,
    "custom_prompts/first_chapter_draft_prompt.txt": first_chapter_draft_prompt,
    "custom_prompts/next_chapter_draft_prompt.txt": next_chapter_draft_prompt,
    "custom_prompts/summarize_recent_chapters_prompt.txt": summarize_recent_chapters_prompt,
    "custom_prompts/summary_prompt.txt": summary_prompt,
    "custom_prompts/update_character_state_prompt.txt": update_character_state_prompt,
    "custom_prompts/volume_summary_prompt.txt": volume_summary_prompt,
    "custom_prompts/knowledge_search_prompt.txt": knowledge_search_prompt,
    "custom_prompts/knowledge_filter_prompt.txt": knowledge_filter_prompt,
    "custom_prompts/create_character_state_prompt.txt": create_character_state_prompt,
    "custom_prompts/system_prompt.txt": ""  # 空文件，等待用户配置
}

def init_prompt_files(force=False):
    """
    初始化提示词文件

    Args:
        force: 是否强制覆盖已存在的文件
    """
    os.makedirs("custom_prompts", exist_ok=True)

    created_count = 0
    skipped_count = 0

    for file_path, content in PROMPT_MAPPING.items():
        if os.path.exists(file_path) and not force:
            print(f"⏭️  跳过已存在的文件: {file_path}")
            skipped_count += 1
            continue

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ 创建文件: {file_path}")
            created_count += 1
        except Exception as e:
            print(f"❌ 创建文件失败 {file_path}: {e}")
            logging.error(f"Failed to create {file_path}: {e}")

    print(f"\n📊 初始化完成: 创建 {created_count} 个文件，跳过 {skipped_count} 个文件")

    # 特别提示 system_prompt.txt
    print("\n💡 提示: custom_prompts/system_prompt.txt 为空，请手动配置全局System Prompt")

if __name__ == "__main__":
    import sys
    import io

    # Windows控制台编码修复
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    force = "--force" in sys.argv

    print("=" * 60)
    print("📦 初始化自定义提示词文件")
    print("=" * 60)
    print()

    if force:
        print("⚠️  强制模式：将覆盖已存在的文件\n")

    init_prompt_files(force=force)

    print("\n" + "=" * 60)
    print("✅ 初始化完成")
    print("=" * 60)



