# volume_utils.py
# -*- coding: utf-8 -*-
"""
分卷相关的工具函数
为长篇小说（>30章）提供分卷管理功能，包含章节分配、卷信息查询和情节提取等核心逻辑
"""
import re
import logging

logging.basicConfig(
    filename='app.log',
    filemode='a',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def calculate_volume_ranges(num_chapters: int, num_volumes: int) -> list:
    """
    计算每卷的章节范围

    原则：
    - 总章节数必须是5的倍数
    - 每卷章节数尽量是5的倍数
    - 章节编号全局累计
    - 最后一卷包含剩余所有章节

    Args:
        num_chapters: 总章节数（建议为5的倍数）
        num_volumes: 分卷数量（0或1表示不分卷）

    Returns:
        [(start, end), ...] 例如 70章分3卷返回 [(1, 20), (21, 40), (41, 70)]

    Examples:
        >>> calculate_volume_ranges(70, 3)
        [(1, 20), (21, 40), (41, 70)]

        >>> calculate_volume_ranges(50, 2)
        [(1, 25), (26, 50)]

        >>> calculate_volume_ranges(30, 1)
        [(1, 30)]
    """
    # 不分卷模式
    if num_volumes <= 1:
        logging.info(f"不分卷模式：总共{num_chapters}章")
        return [(1, num_chapters)]

    # 计算基础每卷章节数（向下取整到5的倍数）
    base = (num_chapters // num_volumes // 5) * 5

    # 如果基础值为0，说明分卷过多，强制每卷至少5章
    if base < 5:
        base = 5
        logging.warning(f"分卷数量过多，强制每卷至少5章。建议减少分卷数至 {num_chapters // 5} 卷以下")

    ranges = []
    start = 1

    for i in range(num_volumes):
        if i < num_volumes - 1:
            # 前面的卷使用基础章节数
            end = start + base - 1
        else:
            # 最后一卷包含所有剩余章节
            end = num_chapters

        ranges.append((start, end))
        logging.info(f"第{i+1}卷: 第{start}-{end}章 (共{end-start+1}章)")
        start = end + 1

    return ranges


def get_volume_number(chapter_num: int, volume_ranges: list) -> int:
    """
    获取章节所属的卷号

    Args:
        chapter_num: 章节编号
        volume_ranges: 卷范围列表 [(start, end), ...]

    Returns:
        卷号（从1开始），若未找到则返回1

    Examples:
        >>> ranges = [(1, 20), (21, 40), (41, 70)]
        >>> get_volume_number(15, ranges)
        1
        >>> get_volume_number(35, ranges)
        2
        >>> get_volume_number(60, ranges)
        3
    """
    for vol_num, (start, end) in enumerate(volume_ranges, 1):
        if start <= chapter_num <= end:
            return vol_num

    logging.warning(f"章节{chapter_num}未找到对应的卷，默认返回第1卷")
    return 1


def is_volume_last_chapter(chapter_num: int, volume_ranges: list) -> bool:
    """
    判断是否是某卷的最后一章

    用于在定稿时触发卷总结生成

    Args:
        chapter_num: 章节编号
        volume_ranges: 卷范围列表 [(start, end), ...]

    Returns:
        True 如果是某卷的最后一章，否则 False

    Examples:
        >>> ranges = [(1, 20), (21, 40), (41, 70)]
        >>> is_volume_last_chapter(20, ranges)
        True
        >>> is_volume_last_chapter(21, ranges)
        False
        >>> is_volume_last_chapter(70, ranges)
        True
    """
    for start, end in volume_ranges:
        if chapter_num == end:
            vol_num = get_volume_number(chapter_num, volume_ranges)
            logging.info(f"检测到第{vol_num}卷的最后一章（第{chapter_num}章），将触发卷总结生成")
            return True
    return False


def extract_volume_plot(volume_architecture: str, volume_num: int) -> str:
    """
    从 Volume_architecture.txt 中提取指定卷的情节规划

    支持多种格式：
    - 第N卷（第X-Y章）
    - 第N卷
    - 卷N

    Args:
        volume_architecture: 分卷架构文本内容
        volume_num: 卷号（从1开始）

    Returns:
        指定卷的情节文本，若未找到则返回空字符串

    Examples:
        >>> text = "第一卷（第1-20章）\\n核心冲突：...\\n\\n第二卷（第21-40章）\\n核心冲突：..."
        >>> extract_volume_plot(text, 1)
        '第一卷（第1-20章）\\n核心冲突：...'
    """
    if not volume_architecture or not volume_architecture.strip():
        logging.warning("分卷架构文本为空，无法提取情节")
        return ""

    # 尝试多种匹配模式
    patterns = [
        # 匹配"第N卷"开头，到下一个卷或文本结尾
        rf"第{volume_num}卷.*?(?=第{volume_num+1}卷|$)",
        # 匹配中文数字"第一卷/第二卷"等
        rf"第[一二三四五六七八九十]+卷.*?(?=第[一二三四五六七八九十]+卷|$)",
        # 匹配"卷N"格式
        rf"卷\s*{volume_num}\s*.*?(?=卷\s*{volume_num+1}|$)",
    ]

    for pattern in patterns:
        match = re.search(pattern, volume_architecture, re.DOTALL)
        if match:
            result = match.group(0).strip()
            logging.info(f"成功提取第{volume_num}卷情节（长度：{len(result)}字）")
            return result

    logging.warning(f"未能提取第{volume_num}卷的情节，使用模式：{patterns[0]}")
    return ""


def validate_volume_config(num_chapters: int, num_volumes: int) -> tuple:
    """
    验证分卷配置的合法性

    验证规则：
    1. 总章节数必须是5的倍数
    2. 分卷数必须 >= 0
    3. 如果分卷，至少需要10章（每卷至少5章）
    4. 分卷数不能超过 num_chapters / 5

    Args:
        num_chapters: 总章节数
        num_volumes: 分卷数量

    Returns:
        (is_valid: bool, error_message: str)

    Examples:
        >>> validate_volume_config(70, 3)
        (True, '')

        >>> validate_volume_config(71, 3)
        (False, '总章节数必须是5的倍数！当前章节数：71')

        >>> validate_volume_config(50, 11)
        (False, '分卷数过多！50章最多分10卷（每卷至少5章）')
    """
    # 验证1：总章节数必须是5的倍数
    if num_chapters % 5 != 0:
        error_msg = f"总章节数必须是5的倍数！当前章节数：{num_chapters}"
        logging.error(error_msg)
        return (False, error_msg)

    # 验证2：分卷数必须 >= 0
    if num_volumes < 0:
        error_msg = f"分卷数量不能为负数！当前值：{num_volumes}"
        logging.error(error_msg)
        return (False, error_msg)

    # 验证3：不分卷模式（0或1）直接通过
    if num_volumes <= 1:
        logging.info("验证通过：不分卷模式")
        return (True, "")

    # 验证4：分卷模式下，至少需要10章
    if num_chapters < 10:
        error_msg = f"分卷模式下至少需要10章！当前章节数：{num_chapters}"
        logging.error(error_msg)
        return (False, error_msg)

    # 验证5：分卷数不能过多（每卷至少5章）
    max_volumes = num_chapters // 5
    if num_volumes > max_volumes:
        error_msg = f"分卷数过多！{num_chapters}章最多分{max_volumes}卷（每卷至少5章）"
        logging.error(error_msg)
        return (False, error_msg)

    logging.info(f"验证通过：{num_chapters}章分{num_volumes}卷")
    return (True, "")


def get_volume_info_text(num_chapters: int, num_volumes: int) -> str:
    """
    生成分卷信息的可读文本（用于UI展示）

    Args:
        num_chapters: 总章节数
        num_volumes: 分卷数量

    Returns:
        格式化的分卷信息文本

    Examples:
        >>> print(get_volume_info_text(70, 3))
        📚 分卷预览（总计70章，分3卷）
        ━━━━━━━━━━━━━━━━━━━━━━
        第1卷: 第1-20章 (共20章)
        第2卷: 第21-40章 (共20章)
        第3卷: 第41-70章 (共30章)
        ━━━━━━━━━━━━━━━━━━━━━━
    """
    if num_volumes <= 1:
        return f"📚 不分卷模式（总计{num_chapters}章）"

    volume_ranges = calculate_volume_ranges(num_chapters, num_volumes)

    lines = [
        f"📚 分卷预览（总计{num_chapters}章，分{num_volumes}卷）",
        "━" * 30
    ]

    for i, (start, end) in enumerate(volume_ranges, 1):
        chapter_count = end - start + 1
        lines.append(f"第{i}卷: 第{start}-{end}章 (共{chapter_count}章)")

    lines.append("━" * 30)

    return "\n".join(lines)


# 模块测试代码
if __name__ == "__main__":
    # 测试 calculate_volume_ranges
    print("测试1: 70章分3卷")
    ranges = calculate_volume_ranges(70, 3)
    print(ranges)
    print()

    # 测试 get_volume_number
    print("测试2: 获取章节所属卷号")
    for ch in [1, 20, 21, 40, 50, 70]:
        vol = get_volume_number(ch, ranges)
        print(f"第{ch}章 → 第{vol}卷")
    print()

    # 测试 is_volume_last_chapter
    print("测试3: 检测卷末章节")
    for ch in [19, 20, 40, 41, 70]:
        is_last = is_volume_last_chapter(ch, ranges)
        print(f"第{ch}章是卷末: {is_last}")
    print()

    # 测试 validate_volume_config
    print("测试4: 验证配置")
    test_cases = [
        (70, 3),   # 合法
        (71, 3),   # 不是5的倍数
        (50, 11),  # 分卷过多
        (30, 1),   # 不分卷
    ]
    for nc, nv in test_cases:
        valid, msg = validate_volume_config(nc, nv)
        print(f"{nc}章{nv}卷: {'✅' if valid else '❌'} {msg}")
    print()

    # 测试 get_volume_info_text
    print("测试5: 生成UI展示文本")
    print(get_volume_info_text(70, 3))