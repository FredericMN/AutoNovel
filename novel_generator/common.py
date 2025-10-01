#novel_generator/common.py
# -*- coding: utf-8 -*-
"""
通用重试、清洗、日志工具
"""
import logging
import re
import time
import traceback
from typing import Optional

logging.basicConfig(
    filename='app.log',      # 日志文件名
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

def debug_log(prompt: str, response_content: str):
    logging.info(
        f"\n[#########################################  Prompt  #########################################]\n{prompt}\n"
    )
    logging.info(
        f"\n[######################################### Response #########################################]\n{response_content}\n"
    )

def invoke_with_cleaning(llm_adapter, prompt: str, max_retries: int = 3, system_prompt: Optional[str] = None) -> str:
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

            # 清理结果中的特殊格式标记
            result = result.replace("```", "").strip()
            if result:
                if retry_count > 0:
                    print(f"✅ 重试成功！（第 {retry_count + 1} 次尝试）")
                    logging.info(f"LLM call succeeded after {retry_count} retries")
                return result

            # 空回复处理
            retry_count += 1
            if retry_count < max_retries:
                # 使用递增等待策略：2秒 -> 4秒 -> 8秒
                wait_time = base_wait_time * retry_count
                wait_time = min(wait_time, 10)  # 最多等待10秒

                print(f"⚠️ LLM 返回空内容 (第 {retry_count}/{max_retries} 次尝试)")
                print(f"   等待 {wait_time} 秒后重试...")
                logging.warning(f"LLM returned empty content, retry {retry_count}/{max_retries}, waiting {wait_time}s")

                time.sleep(wait_time)
            else:
                print(f"❌ LLM 连续 {max_retries} 次返回空内容，生成失败")
                logging.error(f"LLM returned empty content after {max_retries} attempts")
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


