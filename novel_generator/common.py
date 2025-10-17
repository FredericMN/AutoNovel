#novel_generator/common.py
# -*- coding: utf-8 -*-
"""
通用重试、清洗、日志工具
"""
import logging
import re
import time
import traceback
import html
from typing import Optional
from core.utils.file_utils import get_log_file_path

logging.basicConfig(
    filename=get_log_file_path(),      # 日志文件名
    filemode='a',            # 追加模式（'w' 会覆盖）
    level=logging.INFO,      # 记录 INFO 及以上级别的日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def is_rate_limit_error(error: Exception) -> bool:
    """
    判断是否为速率限制错误（429）
    支持检测:
    - Google Gemini: "Resource exhausted"
    - OpenAI: "Rate limit exceeded"
    - 通用 HTTP 429 错误
    """
    error_msg = str(error).lower()
    rate_limit_keywords = [
        "resource exhausted",  # Gemini
        "rate limit",           # OpenAI
        "429",                  # HTTP 状态码
        "quota",                # 配额
        "too many requests",    # 通用
    ]
    return any(keyword in error_msg for keyword in rate_limit_keywords)


def call_with_retry(func, max_retries=3, sleep_time=2, fallback_return=None, **kwargs):
    """
    通用的重试机制封装。
    :param func: 要执行的函数
    :param max_retries: 最大重试次数
    :param sleep_time: 重试前的等待秒数
    :param fallback_return: 如果多次重试仍失败时的返回值
    :param kwargs: 传给func的命名参数
    :return: func的结果，若失败则返回 fallback_return
    """
    for attempt in range(1, max_retries + 1):
        try:
            return func(**kwargs)
        except Exception as e:
            logging.warning(f"[call_with_retry] Attempt {attempt} failed with error: {e}")
            traceback.print_exc()
            if attempt < max_retries:
                time.sleep(sleep_time)
            else:
                logging.error("Max retries reached, returning fallback_return.")
                return fallback_return

def remove_think_tags(text: str) -> str:
    """移除 <think>...</think> 包裹的内容"""
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

def analyze_empty_response(original_text: str) -> tuple[str, str]:
    """
    分析空回复的具体类型，返回 (清理后的文本, 空回复类型)

    Returns:
        tuple: (cleaned_text, empty_type)
        empty_type 可能的值:
        - "valid" - 有效内容
        - "truly_empty" - 真正的空内容
        - "llm_refused" - LLM拒绝回应
        - "only_markup" - 仅包含标记/格式
        - "only_whitespace" - 仅包含空白字符
        - "structured_empty" - 结构化的空回复
    """
    if not original_text:
        return "", "truly_empty"

    # 保存原始文本用于分析
    original_for_analysis = original_text
    cleaned = original_text

    # 检查是否为LLM拒绝回应（在清理前检查，避免误删关键词）
    refuse_patterns = [
        r'我无法.*?生成',
        r'我不能.*?提供',
        r'无法.*?完成',
        r'抱歉.*?无法',
        r'很抱歉.*?不能',
        r'i cannot.*?provide',
        r'i cannot.*?generate',
        r'i\'m unable.*?to',
        r'sorry.*?cannot',
        r'i apologize.*?cannot',
        r'i\'m not able.*?to'
    ]

    for pattern in refuse_patterns:
        if re.search(pattern, original_for_analysis, re.IGNORECASE | re.DOTALL):
            return "", "llm_refused"

    # 清理步骤1: 移除thinking标记（保留内容）
    cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL)

    # 清理步骤2: 移除代码块包裹标记，但保留内容
    # 处理完整的代码块 ```content``` -> content
    cleaned = re.sub(r'```[a-zA-Z]*\n?(.*?)\n?```', r'\1', cleaned, flags=re.DOTALL)
    # 处理单独的```标记
    cleaned = cleaned.replace('```', '')

    # 清理步骤3: 移除HTML注释但保留内容的换行结构
    cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)

    # 清理步骤4: 移除HTML标签
    cleaned = re.sub(r'<[^>]+>', '', cleaned)

    # 清理步骤5: 解码HTML实体为对应字符
    cleaned = html.unescape(cleaned)
    # 将不间断空格转换为普通空格（提高实用性）
    cleaned = cleaned.replace('\xa0', ' ')

    # 清理步骤6: 保守的空白字符处理 - 只清理首尾空白和多余的空行
    # 先统一换行符
    cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
    # 移除过多的连续空行（3个以上换行压缩为2个）
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    # 只清理整体的首尾空白，保留内部缩进结构
    cleaned = cleaned.strip()

    # 检查是否为结构化的空回复
    if cleaned:
        json_patterns = [
            # 只匹配确实为空的content字段：{"content": ""} 或 {"content": null}
            r'^\s*\{\s*["\']?content["\']?\s*:\s*["\']?\s*["\']?\s*\}\s*$',
            r'^\s*\{\s*["\']?content["\']?\s*:\s*null\s*\}\s*$',
            # 空数组和空对象
            r'^\s*\[\s*\]\s*$',
            r'^\s*\{\s*\}\s*$'
        ]

        for pattern in json_patterns:
            if re.search(pattern, cleaned, re.IGNORECASE | re.DOTALL):
                return "", "structured_empty"

    # 判断清理后的结果
    if not cleaned:
        # 检查原文是否仅包含空白
        if re.match(r'^\s*$', original_for_analysis):
            return "", "only_whitespace"
        # 检查是否仅包含标记（但排除原文为空的情况）
        elif original_for_analysis.strip():
            return "", "only_markup"
        else:
            return "", "truly_empty"

    # 对于非空内容，进一步检查是否为有意义的内容
    # 移除过于严格的长度限制，允许数字、百分号等合法短答案
    # 只有当内容确实是无意义的符号时才判定为markup
    if len(cleaned.strip()) <= 3:
        # 先检查是否为无意义的标点符号
        if cleaned.strip() in ['。', '.', '?', '？', '!', '！', '...', '…']:
            # 可能是标点类的无意义回复
            return "", "only_markup"
        # 再检查常见的合法短答案
        elif re.match(r'^[0-9%,\-+]+$', cleaned.strip()):
            # 数字、百分号等（移除句点避免与省略号冲突）
            return cleaned, "valid"
        elif re.match(r'^[是否yesno]+$', cleaned.strip(), re.IGNORECASE):
            # 是否类答案
            return cleaned, "valid"

    return cleaned, "valid"

def debug_log(prompt: str, response_content: str):
    logging.info(
        f"\n[#########################################  Prompt  #########################################]\n{prompt}\n"
    )
    logging.info(
        f"\n[######################################### Response #########################################]\n{response_content}\n"
    )

def invoke_with_cleaning(llm_adapter, prompt: str, max_retries: int = 10, system_prompt: Optional[str] = None) -> str:
    """
    调用 LLM 并清理返回结果，支持附加 system prompt。
    增强功能：
    - 针对 429 错误使用指数退避策略
    - 自动识别速率限制并延长等待时间
    - 空回复时使用递增等待时间重试
    - 向用户汇报所有重试状态
    """
    active_system_prompt = (system_prompt or "").strip()

    print("" + "=" * 50)
    print("发送到 LLM 的提示词:")
    print("-" * 50)
    if active_system_prompt:
        print("[System]")
        print(active_system_prompt)
        print("-" * 50)
    print(prompt)
    print("=" * 50 + "")

    result = ""
    retry_count = 0
    base_wait_time = 2  # 基础等待时间（秒）

    while retry_count < max_retries:
        try:
            result = llm_adapter.invoke(prompt, system_prompt=active_system_prompt)
            print("" + "=" * 50)
            print("LLM 返回的内容:")
            print("-" * 50)
            print(result)
            print("=" * 50 + "")

            # 使用增强的清理和分析逻辑
            cleaned_result, empty_type = analyze_empty_response(result)

            if empty_type == "valid":
                # 有效内容，返回清理后的结果
                if retry_count > 0:
                    print(f"✅ 重试成功！（第 {retry_count + 1} 次尝试）")
                    logging.info(f"LLM call succeeded after {retry_count} retries")
                return cleaned_result

            # 处理各种类型的空回复
            retry_count += 1

            # 根据空回复类型显示不同的提示信息
            empty_type_messages = {
                "truly_empty": "返回真正的空内容",
                "llm_refused": "LLM拒绝回应",
                "only_markup": "仅包含标记/格式符号",
                "only_whitespace": "仅包含空白字符",
                "structured_empty": "返回结构化的空回复"
            }

            empty_msg = empty_type_messages.get(empty_type, "返回空内容")

            if retry_count < max_retries:
                # 使用递增等待策略：2秒 -> 4秒 -> 8秒
                wait_time = base_wait_time * retry_count
                wait_time = min(wait_time, 4)  # 最多等待4秒

                print(f"⚠️ LLM {empty_msg} (第 {retry_count}/{max_retries} 次尝试)")
                print(f"   原始回复: {repr(result[:100])}")  # 显示原始回复的前100字符
                print(f"   等待 {wait_time} 秒后重试...")
                logging.warning(f"LLM empty response - Type: {empty_type}, retry {retry_count}/{max_retries}, waiting {wait_time}s. Original: {repr(result[:200])}")

                time.sleep(wait_time)
            else:
                print(f"❌ LLM 连续 {max_retries} 次{empty_msg}，生成失败")
                print(f"   最后一次回复: {repr(result[:100])}")
                logging.error(f"LLM empty response after {max_retries} attempts - Final type: {empty_type}. Last response: {repr(result[:200])}")
                # 返回空字符串，由上层代码处理
                return ""

        except Exception as e:
            retry_count += 1
            error_msg = str(e)

            # 检测是否为速率限制错误
            if is_rate_limit_error(e):
                # 使用指数退避策略：2^n * base_wait_time
                wait_time = (2 ** retry_count) * base_wait_time
                # 最长等待60秒
                wait_time = min(wait_time, 60)

                print(f"⚠️ 遇到速率限制 (第 {retry_count}/{max_retries} 次尝试)")
                print(f"   错误信息: {error_msg[:100]}...")
                print(f"   等待 {wait_time} 秒后重试...")
                logging.warning(f"[Rate Limit] Attempt {retry_count}/{max_retries}, waiting {wait_time}s. Error: {error_msg[:200]}")

                if retry_count >= max_retries:
                    print(f"❌ 已达到最大重试次数，请稍后再试")
                    logging.error(f"Rate limit exceeded after {max_retries} retries")
                    raise e

                time.sleep(wait_time)

            else:
                # 非速率限制错误，使用普通重试
                print(f"⚠️ 调用失败 (第 {retry_count}/{max_retries} 次尝试)")
                print(f"   错误信息: {error_msg[:100]}...")
                logging.error(f"[LLM Error] Attempt {retry_count}/{max_retries}: {error_msg}")

                if retry_count >= max_retries:
                    print(f"❌ 已达到最大重试次数")
                    logging.error(f"LLM call failed after {max_retries} attempts")
                    raise e

                # 普通错误使用递增等待：2秒 -> 4秒 -> 6秒
                wait_time = base_wait_time * retry_count
                wait_time = min(wait_time, 10)  # 最多等待10秒
                print(f"   等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

    # 理论上不会到达这里（空回复已在循环内返回）
    logging.error("Unexpected: invoke_with_cleaning loop ended without return")
    return result





