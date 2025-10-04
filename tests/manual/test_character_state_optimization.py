#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
角色状态管理优化方案 - 单元测试脚本

测试内容：
1. read_character_dynamics() - 读取角色动力学文件
2. get_context_summary_for_character() - 获取上下文摘要（分卷兼容）
3. 提示词占位符验证
"""

import os
import sys
import tempfile
import shutil
import io

# 设置标准输出编码为 UTF-8（解决 Windows 控制台编码问题）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.utils.file_utils import (
    read_character_dynamics,
    get_context_summary_for_character,
    save_string_to_txt,
    clear_file_content
)
from core.prompting.prompt_definitions import update_character_state_prompt


def test_read_character_dynamics():
    """测试读取角色动力学函数"""
    print("\n" + "="*60)
    print("测试1: read_character_dynamics() 函数")
    print("="*60)

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()

    try:
        # 测试1.1: 文件不存在的情况
        print("\n[测试1.1] 文件不存在的情况")
        result = read_character_dynamics(temp_dir)
        assert result == "", "文件不存在应返回空字符串"
        print("✅ 通过: 文件不存在时返回空字符串")

        # 测试1.2: 文件存在且有内容
        print("\n[测试1.2] 文件存在且有内容")
        test_content = """主角：张三
- 背景：普通学生
- 核心驱动力：寻找失踪的父亲
- 角色弧线：从懦弱到勇敢

反派：李四
- 背景：神秘组织成员
- 核心驱动力：统治世界"""

        char_file = os.path.join(temp_dir, "character_dynamics.txt")
        save_string_to_txt(test_content, char_file)

        result = read_character_dynamics(temp_dir)
        assert result == test_content, "应返回文件完整内容"
        assert "张三" in result, "内容应包含张三"
        assert "李四" in result, "内容应包含李四"
        print(f"✅ 通过: 成功读取文件，长度 {len(result)} 字符")

        # 测试1.3: 文件存在但为空
        print("\n[测试1.3] 文件存在但为空")
        clear_file_content(char_file)
        result = read_character_dynamics(temp_dir)
        assert result == "", "空文件应返回空字符串"
        print("✅ 通过: 空文件时返回空字符串")

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)

    print("\n✅ 测试1 全部通过！\n")


def test_get_context_summary_for_character():
    """测试获取上下文摘要函数（分卷兼容）"""
    print("\n" + "="*60)
    print("测试2: get_context_summary_for_character() 函数")
    print("="*60)

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()

    try:
        # 准备测试数据
        global_summary = "主角张三在第1-5章经历了XXX事件，获得了YYY能力。"
        volume_1_summary = "第一卷：张三从普通学生成长为修炼者，打败了李四。"
        volume_2_summary = "第二卷：张三进入宗门，遇到了新的挑战。"

        global_file = os.path.join(temp_dir, "global_summary.txt")
        vol1_file = os.path.join(temp_dir, "volume_1_summary.txt")
        vol2_file = os.path.join(temp_dir, "volume_2_summary.txt")

        save_string_to_txt(global_summary, global_file)
        save_string_to_txt(volume_1_summary, vol1_file)
        save_string_to_txt(volume_2_summary, vol2_file)

        # 测试2.1: 非分卷模式
        print("\n[测试2.1] 非分卷模式（num_volumes=0）")
        result = get_context_summary_for_character(
            filepath=temp_dir,
            chapter_num=5,
            num_volumes=0,
            total_chapters=30
        )
        assert result == global_summary, "非分卷模式应仅返回 global_summary"
        print("✅ 通过: 非分卷模式返回 global_summary")

        # 测试2.2: 非分卷模式（num_volumes=1）
        print("\n[测试2.2] 非分卷模式（num_volumes=1）")
        result = get_context_summary_for_character(
            filepath=temp_dir,
            chapter_num=5,
            num_volumes=1,
            total_chapters=30
        )
        assert result == global_summary, "num_volumes=1 应仅返回 global_summary"
        print("✅ 通过: num_volumes=1 返回 global_summary")

        # 测试2.3: 第一卷（分卷模式）
        print("\n[测试2.3] 第一卷（分卷模式，70章分3卷）")
        result = get_context_summary_for_character(
            filepath=temp_dir,
            chapter_num=15,  # 第一卷范围内（1-20章）
            num_volumes=3,
            total_chapters=70
        )
        assert result == global_summary, "第一卷应仅返回 global_summary"
        print("✅ 通过: 第一卷返回 global_summary")

        # 测试2.4: 第二卷（分卷模式）
        print("\n[测试2.4] 第二卷（分卷模式，70章分3卷）")
        result = get_context_summary_for_character(
            filepath=temp_dir,
            chapter_num=30,  # 第二卷范围内（21-40章）
            num_volumes=3,
            total_chapters=70
        )
        assert "【上一卷完整摘要】" in result, "第二卷应包含上一卷摘要"
        assert "【本卷累积摘要】" in result, "第二卷应包含本卷摘要"
        assert volume_1_summary in result, "应包含第一卷摘要内容"
        assert global_summary in result, "应包含全局摘要内容"
        print("✅ 通过: 第二卷返回组合摘要")
        print(f"   返回内容预览:\n{result[:200]}...")

        # 测试2.5: 第三卷（分卷模式）
        print("\n[测试2.5] 第三卷（分卷模式，70章分3卷）")
        result = get_context_summary_for_character(
            filepath=temp_dir,
            chapter_num=60,  # 第三卷范围内（41-70章）
            num_volumes=3,
            total_chapters=70
        )
        assert "【上一卷完整摘要】" in result, "第三卷应包含上一卷摘要"
        assert volume_2_summary in result, "应包含第二卷摘要内容"
        print("✅ 通过: 第三卷返回组合摘要（包含第二卷）")

        # 测试2.6: 异常参数处理（total_chapters <= 0）
        print("\n[测试2.6] 异常参数处理（total_chapters=0）")
        result = get_context_summary_for_character(
            filepath=temp_dir,
            chapter_num=30,
            num_volumes=3,
            total_chapters=0  # 异常值
        )
        assert result == global_summary, "total_chapters异常时应回退到 global_summary"
        print("✅ 通过: 异常参数时安全回退")

        # 测试2.7: 上一卷摘要缺失的情况
        print("\n[测试2.7] 上一卷摘要缺失的情况")
        os.remove(vol1_file)  # 删除第一卷摘要
        result = get_context_summary_for_character(
            filepath=temp_dir,
            chapter_num=30,
            num_volumes=3,
            total_chapters=70
        )
        assert "（上一卷摘要缺失）" in result, "上一卷摘要缺失时应显示提示"
        print("✅ 通过: 上一卷摘要缺失时显示提示信息")

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)

    print("\n✅ 测试2 全部通过！\n")


def test_prompt_placeholders():
    """测试提示词占位符"""
    print("\n" + "="*60)
    print("测试3: 提示词占位符验证")
    print("="*60)

    # 测试3.1: 检查提示词是否包含所有必需占位符
    print("\n[测试3.1] 检查默认提示词占位符")
    required_placeholders = [
        "{chapter_text}",
        "{character_dynamics}",
        "{context_summary}",
        "{old_state}"
    ]

    for placeholder in required_placeholders:
        assert placeholder in update_character_state_prompt, \
            f"提示词缺少占位符: {placeholder}"
        print(f"✅ 找到占位符: {placeholder}")

    # 测试3.2: 验证提示词可以正常格式化
    print("\n[测试3.2] 验证提示词格式化")
    test_data = {
        "chapter_text": "第一章：测试章节内容...",
        "character_dynamics": "主角：张三\n核心驱动力：XXX",
        "context_summary": "前文摘要：张三经历了YYY事件",
        "old_state": "旧的角色状态..."
    }

    try:
        formatted_prompt = update_character_state_prompt.format(**test_data)
        assert "第一章：测试章节内容" in formatted_prompt
        assert "主角：张三" in formatted_prompt
        assert "前文摘要：张三经历了YYY事件" in formatted_prompt
        print("✅ 提示词格式化成功")
        print(f"   格式化后长度: {len(formatted_prompt)} 字符")
    except KeyError as e:
        print(f"❌ 格式化失败，缺少占位符: {e}")
        raise

    # 测试3.3: 检查关键指令是否存在
    print("\n[测试3.3] 检查关键指令")
    key_instructions = [
        "核心角色识别与保护",
        "角色降级与清理策略",
        "S级 - 核心角色",
        "A级 - 非核心主要角色",
        "B级 - 临时角色",
        "【已死亡】"
    ]

    for instruction in key_instructions:
        assert instruction in update_character_state_prompt, \
            f"提示词缺少关键指令: {instruction}"
        print(f"✅ 找到关键指令: {instruction}")

    print("\n✅ 测试3 全部通过！\n")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始角色状态管理优化方案单元测试")
    print("="*60)

    test_results = []

    # 测试1: read_character_dynamics
    try:
        test_read_character_dynamics()
        test_results.append(("read_character_dynamics", True))
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        test_results.append(("read_character_dynamics", False))

    # 测试2: get_context_summary_for_character
    try:
        test_get_context_summary_for_character()
        test_results.append(("get_context_summary_for_character", True))
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        test_results.append(("get_context_summary_for_character", False))

    # 测试3: 提示词占位符
    try:
        test_prompt_placeholders()
        test_results.append(("prompt_placeholders", True))
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        test_results.append(("prompt_placeholders", False))

    # 输出测试总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    total = len(test_results)
    passed = sum(1 for _, result in test_results if result)

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status}: {test_name}")

    print(f"\n总计: {passed}/{total} 项测试通过")

    if passed == total:
        print("\n🎉 所有测试全部通过！优化方案核心逻辑验证成功！")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 项测试失败，请检查相关代码")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
