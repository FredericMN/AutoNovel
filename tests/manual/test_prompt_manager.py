# test_prompt_manager.py
# -*- coding: utf-8 -*-
"""
测试PromptManager和可选模块功能
"""
import sys
import io
from prompt_manager import PromptManager

# Windows控制台编码修复
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_basic_functionality():
    """测试PromptManager基础功能"""
    print("=" * 60)
    print("📋 测试PromptManager基础功能")
    print("=" * 60)

    pm = PromptManager()

    # 测试1：加载配置
    print("\n▶ 测试1：配置加载")
    modules = pm.get_all_modules()
    total_modules = sum(len(category) for category in modules.values())
    print(f"   └─ ✅ 成功加载 {total_modules} 个模块配置")

    # 测试2：检查模块启用状态
    print("\n▶ 测试2：模块启用状态")
    test_modules = [
        ("architecture", "core_seed", True),
        ("architecture", "character_dynamics", True),
        ("architecture", "world_building", True),
        ("architecture", "plot_architecture", True),
        ("helper", "global_system", False),
    ]
    for category, name, expected in test_modules:
        enabled = pm.is_module_enabled(category, name)
        status = "✅" if enabled == expected else "❌"
        print(f"   {status} {category}.{name}: {enabled} (期望: {expected})")

    # 测试3：获取提示词
    print("\n▶ 测试3：获取提示词")
    prompt = pm.get_prompt("architecture", "core_seed")
    if prompt and len(prompt) > 0:
        print(f"   └─ ✅ 成功获取提示词 (长度: {len(prompt)}字)")
    else:
        print("   └─ ❌ 提示词获取失败")

    # 测试4：必需模块检查
    print("\n▶ 测试4：必需模块标识")
    required_modules = [
        ("architecture", "core_seed"),
        ("blueprint", "chapter_blueprint"),
        ("chapter", "first_chapter"),
    ]
    for category, name in required_modules:
        info = pm.get_module_info(category, name)
        if info and info.get("required"):
            print(f"   ✅ {category}.{name}: 必需模块")
        else:
            print(f"   ❌ {category}.{name}: 非必需模块（配置错误！）")

def test_module_toggle():
    """测试模块启用/禁用功能"""
    print("\n" + "=" * 60)
    print("🔄 测试模块启用/禁用")
    print("=" * 60)

    pm = PromptManager()

    # 测试禁用可选模块
    print("\n▶ 测试禁用可选模块（角色动力学）")
    try:
        pm.toggle_module("architecture", "character_dynamics", False)
        enabled = pm.is_module_enabled("architecture", "character_dynamics")
        if not enabled:
            print("   └─ ✅ 模块已成功禁用")
        else:
            print("   └─ ❌ 模块禁用失败")

        # 恢复启用
        pm.toggle_module("architecture", "character_dynamics", True)
        print("   └─ ✅ 模块已恢复启用")
    except Exception as e:
        print(f"   └─ ❌ 测试失败: {e}")

    # 测试禁用必需模块（应该失败）
    print("\n▶ 测试禁用必需模块（核心种子）")
    try:
        pm.toggle_module("architecture", "core_seed", False)
        print("   └─ ❌ 不应该允许禁用必需模块")
    except ValueError as e:
        print(f"   └─ ✅ 正确拒绝: {str(e)}")
    except Exception as e:
        print(f"   └─ ❌ 未预期的错误: {e}")

def test_prompt_loading():
    """测试提示词加载优先级"""
    print("\n" + "=" * 60)
    print("📥 测试提示词加载优先级")
    print("=" * 60)

    pm = PromptManager()

    print("\n▶ 测试：custom_prompts/*.txt 优先于默认值")
    # 测试自定义文件存在时的优先级
    import os
    test_file = "custom_prompts/core_seed_prompt.txt"
    if os.path.exists(test_file):
        prompt = pm.get_prompt("architecture", "core_seed")
        if prompt:
            print(f"   └─ ✅ 成功从文件加载提示词 ({len(prompt)}字)")
        else:
            print("   └─ ❌ 提示词加载失败")
    else:
        print("   └─ ⚠️ 测试文件不存在，跳过")

def test_architecture_integration():
    """测试与architecture.py的集成"""
    print("\n" + "=" * 60)
    print("🔗 测试与architecture.py集成")
    print("=" * 60)

    print("\n▶ 测试：PromptManager导入")
    try:
        from novel_generator.architecture import PromptManager as ArchPM
        print("   └─ ✅ architecture.py成功导入PromptManager")
    except ImportError as e:
        print(f"   └─ ❌ 导入失败: {e}")

    print("\n▶ 测试：禁用模块后的预期行为")
    pm = PromptManager()

    # 模拟禁用角色动力学
    pm.toggle_module("architecture", "character_dynamics", False)
    enabled = pm.is_module_enabled("architecture", "character_dynamics")
    if not enabled:
        print("   ├─ ✅ 角色动力学已禁用")
        print("   └─ 📝 预期输出：'（已跳过角色动力学生成）'")
    else:
        print("   └─ ❌ 模块禁用失败")

    # 恢复启用
    pm.toggle_module("architecture", "character_dynamics", True)

if __name__ == "__main__":
    print("\n🧪 开始测试提示词管理系统\n")

    test_basic_functionality()
    test_module_toggle()
    test_prompt_loading()
    test_architecture_integration()

    print("\n" + "=" * 60)
    print("✅ 测试完成")
    print("=" * 60)
