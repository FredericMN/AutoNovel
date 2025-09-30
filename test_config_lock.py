#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试配置锁定机制
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.validation_utils import check_critical_files_exist

def test_config_lock():
    """测试配置锁定检测"""
    test_path = "D:/AI/Novel3"

    print(f"检测项目路径: {test_path}")
    print("-" * 50)

    result = check_critical_files_exist(test_path)

    print("检测结果:")
    print(f"  架构文件存在: {result['architecture_exists']}")
    print(f"  目录文件存在: {result['directory_exists']}")
    print(f"  分卷架构存在: {result['volume_architecture_exists']}")
    print(f"  章节文件存在: {result['any_chapter_exists']}")
    print("-" * 50)
    print(f"  应该锁定: {result['is_locked']}")

    if result['is_locked']:
        print("\n配置已锁定，章节数和分卷数参数将被禁用")
    else:
        print("\n配置未锁定，可以自由修改")

if __name__ == "__main__":
    test_config_lock()