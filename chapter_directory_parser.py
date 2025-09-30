# chapter_blueprint_parser.py
# -*- coding: utf-8 -*-
import re

CHINESE_NUM_MAP = {
    '零': 0, '〇': 0,
    '一': 1, '二': 2, '两': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10, '百': 100, '千': 1000, '万': 10000
}

LABEL_SYNONYMS = {
    'chapter_role': [r'本章定位', r'章节定位', r'本章角色定位', r'定位'],
    'chapter_purpose': [r'核心作用', r'核心目的', r'章节目的', r'内容作用', r'核心目标', r'本章目标'],
    'suspense_level': [r'悬念密度', r'悬念强度', r'悬疑密度', r'悬疑强度', r'悬念节奏'],
    'foreshadowing': [r'伏笔操作', r'伏笔设计', r'伏笔安排', r'伏笔'],
    'plot_twist_level': [r'认知颠覆', r'转折程度', r'反转强度', r'反转程度', r'颠覆程度'],
    'chapter_summary': [r'本章简述', r'章节简述', r'一句话概括', r'章节概述', r'本章概述']
}

# Precompile label regexes accepting both Chinese and English colons
# 支持格式：
#   - 本章定位：内容
#   - * 本章定位：内容
#   - *   **本章定位：** 内容
#   - **本章定位：** 内容
LABEL_REGEXES = {
    key: [re.compile(
        r'^\s*' +                            # 行首空白
        r'(?:[*\-•]\s+)?' +                  # 可选列表标记 + 空格
        r'\*{0,2}\s*' +                      # 可选粗体开始（0-2个星号）
        r'(?:' + alias + r')' +              # 字段名
        r'\s*[:：]\s*' +                     # 冒号（可能在粗体内或外）
        r'\*{0,2}\s*' +                      # 可选粗体结束
        r'(.+?)\s*' +                        # 捕获内容（至少1个字符，非贪婪）
        r'\*{0,2}\s*$',                      # 可选结尾粗体
        re.IGNORECASE
    ) for alias in aliases]
    for key, aliases in LABEL_SYNONYMS.items()
}

# 卷标题识别（支持 ### **第一卷：楼中囚神** 和数字卷号）
VOLUME_DIGIT_RE = re.compile(
    r'^\s*[#*\-\s]*' +                       # 开头的标记和空格（井号、星号、破折号、空格）
    r'第\s*(?P<num>\d+)\s*卷' +              # 第X卷
    r'\s*[:：]?\s*' +                        # 可选冒号
    r'(?P<title>[^#*\-]+?)' +                # 标题（不包含标记符号，非贪婪）
    r'\s*[#*\-\s]*$',                        # 结尾的标记和空格
    re.IGNORECASE
)
VOLUME_CHINESE_RE = re.compile(
    r'^\s*[#*\-\s]*' +                       # 开头的标记和空格
    r'第(?P<cnum>[零〇一二两三四五六七八九十百千万]+)卷' +  # 第X卷（中文数字）
    r'\s*[:：]?\s*' +                        # 可选冒号
    r'(?P<title>[^#*\-]+?)' +                # 标题（不包含标记符号，非贪婪）
    r'\s*[#*\-\s]*$'                         # 结尾的标记和空格
)

# 章节标题识别（增强支持 #### **第11章 - 标题** 和多种前缀组合）
HEADER_LINE_MARKERS = re.compile(r'^(?:\s*[#]{1,6}\s*|\s*[*>]{1,3}\s*)+')

DIGIT_HEADER_RE = re.compile(r'^\s*[#*\-]*\s*第\s*(?P<num>\d+)\s*章.*$', re.IGNORECASE)
CHINESE_HEADER_RE = re.compile(r'^\s*[#*\-]*\s*第(?P<cnum>[零〇一二两三四五六七八九十百千万]+)章.*$')
ANY_HEADER_RE = re.compile(r'第\s*([\d零〇一二两三四五六七八九十百千万]*)\s*章')

SEPARATOR_AFTER_ZHANG = re.compile(r'[\s\-–—:：|·•~]+')


def _strip_md_wrappers(s: str) -> str:
    s = s.strip()
    # strip bold/italic wrappers and markdown markers
    s = re.sub(r'^[#*_\-]+\s*', '', s)
    s = re.sub(r'\s*[*_\-]+$', '', s)
    return s.strip()


def _to_int_from_chinese(num_str: str) -> int:
    """Convert Chinese numerals up to 万级"""
    if not num_str:
        return 0
    total = 0
    section = 0
    number = 0
    for ch in num_str:
        val = CHINESE_NUM_MAP.get(ch, None)
        if val is None:
            continue
        if val == 10 or val == 100 or val == 1000:
            if number == 0:
                number = 1
            section += number * val
            number = 0
        elif val == 10000:
            section = (section + number) * 10000
            total += section
            section = 0
            number = 0
        else:
            number = val
    return total + section + number


def _extract_volume(line: str):
    """解析卷标题行，返回 (volume_number:int|None, volume_title:str)"""
    raw = line.strip()
    # 清理 Markdown 符号
    raw = re.sub(r'^[#*\-\s]+', '', raw)
    raw = re.sub(r'[#*\-\s]+$', '', raw)

    # 尝试数字卷号
    m = VOLUME_DIGIT_RE.match(line)
    if m:
        return int(m.group('num')), m.group('title').strip()

    # 尝试中文卷号
    m = VOLUME_CHINESE_RE.match(line)
    if m:
        num = _to_int_from_chinese(m.group('cnum'))
        return num, m.group('title').strip()

    return None, ''


def _extract_header(line: str, last_num):
    """Try to parse header line. Return (chapter_number:int|None, title:str)."""
    raw = line.strip()
    if HEADER_LINE_MARKERS.match(raw):
        raw = HEADER_LINE_MARKERS.sub('', raw).strip()
    raw = _strip_md_wrappers(raw)

    m = DIGIT_HEADER_RE.match(raw)
    if m:
        num = int(m.group('num'))
    else:
        m2 = CHINESE_HEADER_RE.match(raw)
        if m2:
            num = _to_int_from_chinese(m2.group('cnum')) or None
        else:
            # Allow bare '第章'
            m3 = ANY_HEADER_RE.search(raw)
            num = None
            if m3 and (m3.group(1) == '' or m3.group(1) is None):
                # missing number, will infer later
                num = None

    # Extract title part after '章'
    title = ''
    if '章' in raw:
        after = raw.split('章', 1)[1]
        after = SEPARATOR_AFTER_ZHANG.sub(' ', after).strip()
        # Remove common wrappers
        after = after.strip('[]《》"""')
        title = after

    # Infer missing num
    if num is None and last_num is not None:
        num = last_num + 1
    return num, title



def parse_chapter_blueprint(blueprint_text: str):
    """
    更鲁棒的解析（增强版）：
    - 支持分卷模式：识别 ### **第一卷：楼中囚神** 格式
    - 支持多种章节标题格式：#### **第11章 - 标题**、*第1章*、第1章 等
    - 兼容 Markdown 粗体/标题符、全角/半角冒号、连字符/破折号/空格分隔
    - 兼容中文数字（第一章）、缺数字（"第章" → 顺延编号）、标题可带[]/《》
    - 标签字段支持多种同义词：定位/目的/悬念/伏笔/颠覆/简述

    返回列表：[{
        chapter_number, chapter_title, chapter_role, chapter_purpose,
        suspense_level, foreshadowing, plot_twist_level, chapter_summary,
        volume_number, volume_title  # 新增卷信息
    }]
    """
    lines = [ln.rstrip() for ln in blueprint_text.splitlines()]
    results = []
    current = None
    last_num = None
    current_volume_num = None
    current_volume_title = ''

    def finalize_current():
        if not current:
            return
        if not current['chapter_title']:
            current['chapter_title'] = f"第{current['chapter_number']}章"
        # 注入当前卷信息
        current['volume_number'] = current_volume_num
        current['volume_title'] = current_volume_title
        results.append(current)

    for ln in lines:
        if not ln.strip():
            continue

        # 尝试识别卷标题
        vol_num, vol_title = _extract_volume(ln)
        if vol_num is not None:
            current_volume_num = vol_num
            current_volume_title = vol_title
            continue

        # 尝试识别章节标题
        any_hdr = ANY_HEADER_RE.search(ln)
        num, title = _extract_header(ln, last_num)
        if any_hdr is not None:
            if num is None:
                num = (last_num + 1) if last_num else 1
            finalize_current()
            current = {
                'chapter_number': num,
                'chapter_title': title,
                'chapter_role': '',
                'chapter_purpose': '',
                'suspense_level': '',
                'foreshadowing': '',
                'plot_twist_level': '',
                'chapter_summary': '',
                'volume_number': None,
                'volume_title': ''
            }
            last_num = num
            continue

        # 解析字段内容
        if current:
            norm = _strip_md_wrappers(ln)
            norm = norm.replace('：', ':')
            for key, regex_list in LABEL_REGEXES.items():
                for rgx in regex_list:
                    m = rgx.match(norm)
                    if m:
                        val = m.group(1).strip()
                        # 清理值中的方括号和残留的粗体标记
                        val = val.strip('[]')
                        val = re.sub(r'^\*{1,2}\s*', '', val)  # 开头的粗体
                        val = re.sub(r'\s*\*{1,2}$', '', val)  # 结尾的粗体
                        current[key] = val.strip()
                        break
                else:
                    continue
                break

    finalize_current()
    results.sort(key=lambda x: x['chapter_number'])
    return results

def get_chapter_info_from_blueprint(blueprint_text: str, target_chapter_number: int):
    """
    在已经加载好的章节蓝图文本中，找到对应章号的结构化信息；
    兼容：若找不到精确匹配，则按序号回退（列表下标 target-1），避免因格式瑕疵导致完全丢失目录。
    返回包含卷信息的完整章节数据。
    """
    all_chapters = parse_chapter_blueprint(blueprint_text)
    for ch in all_chapters:
        if ch['chapter_number'] == target_chapter_number:
            return ch
    # 顺序回退：若至少有 target_chapter_number 个条目，则取第 target-1 个
    if 1 <= target_chapter_number <= len(all_chapters):
        return all_chapters[target_chapter_number - 1]
    # 默认返回（包含卷信息字段）
    return {
        "chapter_number": target_chapter_number,
        "chapter_title": f"第{target_chapter_number}章",
        "chapter_role": "",
        "chapter_purpose": "",
        "suspense_level": "",
        "foreshadowing": "",
        "plot_twist_level": "",
        "chapter_summary": "",
        "volume_number": None,
        "volume_title": ""
    }



