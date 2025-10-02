# -*- coding: utf-8 -*-
r"""
测试剧情要点智能压缩功能

使用方法：
python tests/manual/test_plot_arcs_compress.py "D:\Novel\project\001-末日种田\plot_arcs.txt"
"""

import sys
import os
import io
import re  # 用于宽松匹配伏笔格式

# Windows控制台编码修复
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.prompting.prompt_definitions import (
    plot_arcs_compress_auto_prompt
)

def analyze_plot_arcs(file_path):
    """分析剧情要点文件"""
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 统计未解决和已解决的伏笔数量（宽松匹配，与finalization.py保持一致）
    lines = content.split('\n')

    # 未解决伏笔：匹配 [A级-...] 或 [B级-...] 或 [C级-...]，允许前导符号和空格
    unresolved_pattern = r'^\s*[-•·\*]?\s*\[([ABC]级[-\s]*[^\]]+)\]'
    unresolved = [line for line in lines if re.match(unresolved_pattern, line.strip())]

    # 已解决伏笔：匹配 ✓已解决 或 ✅已解决 或 已解决: 等变体
    resolved_pattern = r'^\s*[-•·\*]?\s*[✓✅☑]\s*已解决[:：]?'
    resolved = [line for line in lines if re.match(resolved_pattern, line.strip())]

    print("=" * 60)
    print("=== 当前状态分析 ===")
    print("=" * 60)
    print(f"文件路径: {file_path}")
    print(f"文件大小: {len(content)} 字符")
    print(f"总行数: {len(lines)}")
    print(f"未解决伏笔: {len(unresolved)} 条")
    print(f"已解决伏笔: {len(resolved)} 条")
    print()

    # 显示前10条未解决伏笔
    print("=== 前10条未解决伏笔 ===")
    for i, line in enumerate(unresolved[:10], 1):
        print(f"  {i}. {line.strip()}")  # 显示完整行（包含分级标签）
    print()

    # 显示最后5条已解决伏笔
    print("=== 最近5条已解决伏笔 ===")
    for i, line in enumerate(resolved[-5:], 1):
        # 移除已解决标记前缀，提取内容
        cleaned = re.sub(r'^\s*[-•·\*]?\s*[✓✅☑]\s*已解决[:：]?\s*', '', line.strip())
        print(f"  {i}. {cleaned}")
    print()

    # 判断是否需要压缩
    if len(unresolved) > 50 or len(resolved) > 20:
        print("[警告] 超过压缩阈值！")
        print(f"   - 未解决伏笔阈值: 50 (当前: {len(unresolved)})")
        print(f"   - 已解决伏笔阈值: 20 (当前: {len(resolved)})")
        print()
        print("[建议操作]")
        print("   1. 在定稿第50章、第60章等10的倍数章节时，系统将自动触发压缩")
        print("   2. 或者手动运行以下命令测试压缩提示词：")
        print()
        print("   # 智能自动压缩（基于已分级的剧情要点）")
        print(f"   python -c \"from core.prompting.prompt_definitions import plot_arcs_compress_auto_prompt; print(plot_arcs_compress_auto_prompt.format(...))\"")
    else:
        print("[正常] 未达到压缩阈值，暂不需要压缩")

    print()
    print("=" * 60)
    print("=== 配置信息 ===")
    print("=" * 60)
    print("压缩触发条件:")
    print("  1. 章节号是10的倍数（10、20、30...）")
    print("  2. 未解决伏笔 > 50条 OR 已解决伏笔 > 20条")
    print()
    print("伏笔格式匹配（宽松）:")
    print("  - 未解决：支持 [A级-...]、[B级-...]、[C级-...]")
    print("            允许前导符号（-、•、·、*）和空格")
    print("  - 已解决：支持 ✓已解决、✅已解决、☑已解决")
    print("            允许冒号（:、：）和空格变体")
    print()
    print("压缩规则:")
    print("  - [A级-主线]: 强制≤30条（相关伏笔合并）")
    print("  - [B级-支线]: ≤10条（保留最近20章）")
    print("  - [C级-细节]: ≤3条（保留最近3章）")
    print("  - 已解决伏笔: ≤10条（保留最近10章）")
    print()
    print("目标:")
    print("  - 未解决伏笔: ≤40条")
    print("  - 已解决伏笔: ≤10条")
    print("=" * 60)

def main():
    if len(sys.argv) < 2:
        print("用法: python test_plot_arcs_compress.py <plot_arcs.txt路径>")
        print()
        print("示例:")
        print('  python tests/manual/test_plot_arcs_compress.py "D:\\Novel\\project\\001-末日种田\\plot_arcs.txt"')
        return

    file_path = sys.argv[1]
    analyze_plot_arcs(file_path)

if __name__ == "__main__":
    main()
