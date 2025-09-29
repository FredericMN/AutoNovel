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
LABEL_REGEXES = {
    key: [re.compile(r'^\s*(?:[*\-•]\s*)?(?:' + alias + r')\s*[:：]\s*(.*)\s*$', re.IGNORECASE)
          for alias in aliases]
    for key, aliases in LABEL_SYNONYMS.items()
}

HEADER_LINE_MARKERS = re.compile(r'^(?:\s*[#]{1,6}\s*|\s*[>*]\s*)')

DIGIT_HEADER_RE = re.compile(r'^\s*(?:\*{1,3}\s*)?第\s*(?P<num>\d+)\s*章.*$', re.IGNORECASE)
CHINESE_HEADER_RE = re.compile(r'^\s*(?:\*{1,3}\s*)?第(?P<cnum>[零〇一二两三四五六七八九十百千万]+)章.*$')
ANY_HEADER_RE = re.compile(r'第\s*([\d零〇一二两三四五六七八九十百千万]*)\s*章')

SEPARATOR_AFTER_ZHANG = re.compile(r'[\s\-–—:：|·•~]+')


def _strip_md_wrappers(s: str) -> str:
    s = s.strip()
    # strip bold/italic wrappers
    s = re.sub(r'^[*_]{1,3}\s*', '', s)
    s = re.sub(r'\s*[*_]{1,3}$', '', s)
    return s.strip()


def _to_int_from_chinese(num_str: str) -> int:
    # Convert Chinese numerals up to 万级
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
        after = after.strip('[]《》"“”')
        title = after

    # Infer missing num
    if num is None and last_num is not None:
        num = last_num + 1
    return num, title



def parse_chapter_blueprint(blueprint_text: str):
    """
    更鲁棒的解析：
    - 扫描整份文本，遇到标题行（第n章…）开始新章节块；
    - 兼容 Markdown 粗体/标题符、全角/半角冒号、连字符/破折号/空格分隔；
    - 兼容中文数字（第一章）、缺数字（"第章" → 顺延编号）、标题可带[]/《》；
    - 标签字段支持多种同义词：定位/目的/悬念/伏笔/颠覆/简述。
    返回列表：[{chapter_number, chapter_title, chapter_role, chapter_purpose, suspense_level, foreshadowing, plot_twist_level, chapter_summary}]
    """
    lines = [ln.rstrip() for ln in blueprint_text.splitlines()]
    results = []
    current = None
    last_num = None

    def finalize_current():
        if not current:
            return
        if not current['chapter_title']:
            current['chapter_title'] = f"第{current['chapter_number']}章"
        results.append(current)

    for ln in lines:
        if not ln.strip():
            continue
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
                'chapter_summary': ''
            }
            last_num = num
            continue
        if current:
            norm = _strip_md_wrappers(ln)
            norm = norm.replace('：', ':')
            for key, regex_list in LABEL_REGEXES.items():
                for rgx in regex_list:
                    m = rgx.match(norm)
                    if m:
                        val = m.group(1).strip()
                        val = val.strip('[]')
                        current[key] = val
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
    """
    all_chapters = parse_chapter_blueprint(blueprint_text)
    for ch in all_chapters:
        if ch['chapter_number'] == target_chapter_number:
            return ch
    # 顺序回退：若至少有 target_chapter_number 个条目，则取第 target-1 个
    if 1 <= target_chapter_number <= len(all_chapters):
        return all_chapters[target_chapter_number - 1]
    # 默认返回
    return {
        "chapter_number": target_chapter_number,
        "chapter_title": f"第{target_chapter_number}章",
        "chapter_role": "",
        "chapter_purpose": "",
        "suspense_level": "",
        "foreshadowing": "",
        "plot_twist_level": "",
        "chapter_summary": ""
    }



