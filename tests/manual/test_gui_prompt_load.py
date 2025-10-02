# -*- coding: utf-8 -*-
"""
测试 GUI 提示词动态加载

验证新增的提示词模块是否能被 GUI 正确识别
"""
import sys
import os
import io

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Windows 控制台编码修复
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from core.prompting.prompt_manager import PromptManager

def test_prompt_manager():
    print("=" * 60)
    print("=== 测试 PromptManager 动态加载 ===")
    print("=" * 60)
    print()

    pm = PromptManager()
    modules = pm.get_all_modules()

    # 检查 finalization 分类
    if "finalization" in modules:
        finalization_modules = modules["finalization"]
        print(f"[finalization] 模块数量: {len(finalization_modules)}")
        print()

        # 检查剧情要点管理模块
        new_modules = ["plot_arcs_update", "plot_arcs_compress_auto", "plot_arcs_distill"]

        for module_name in new_modules:
            if module_name in finalization_modules:
                info = finalization_modules[module_name]
                print(f"✅ {module_name}")
                print(f"   - 显示名称: {info.get('display_name', 'N/A')}")
                print(f"   - 是否启用: {info.get('enabled', False)}")
                print(f"   - 文件路径: {info.get('file', 'N/A')}")
                print(f"   - 描述: {info.get('description', 'N/A')}")
                print(f"   - 支持变量: {info.get('variables', [])}")

                # 检查文件是否存在
                file_path = info.get('file', '')
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    print(f"   - 文件大小: {file_size} 字节")
                    print("   - 文件状态: 存在 ✅")
                else:
                    print("   - 文件状态: 不存在 ❌")
                print()
            else:
                print(f"❌ {module_name} - 未找到！")
                print()

        # 列出所有 finalization 模块
        print("=== 所有 finalization 模块 ===")
        for name in finalization_modules.keys():
            enabled = finalization_modules[name].get('enabled', False)
            status = "✅" if enabled else "❌"
            print(f"{status} {name}")
        print()

    else:
        print("❌ 未找到 finalization 分类")

    print("=" * 60)
    print("=== 测试 PromptManager 读取提示词 ===")
    print("=" * 60)
    print()

    # 测试读取剧情要点管理提示词
    for module_name in ["plot_arcs_update", "plot_arcs_compress_auto", "plot_arcs_distill"]:
        print(f"测试读取: {module_name}")
        prompt = pm.get_prompt("finalization", module_name)
        if prompt:
            print(f"   ✅ 成功读取 ({len(prompt)} 字符)")
            print(f"   预览: {prompt[:100]}...")
        else:
            print(f"   ❌ 读取失败")
        print()

    print("=" * 60)
    print("=== 测试完成 ===")
    print("=" * 60)

if __name__ == "__main__":
    test_prompt_manager()
