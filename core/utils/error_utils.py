"""
错误识别相关工具函数（跨模块复用）
"""

import re
from typing import Any


# 速率限制相关的关键词列表（供 is_rate_limit_error 和 is_rate_limit_text 共用）
_RATE_LIMIT_KEYWORDS = [
    "resource exhausted",  # Gemini
    "rate limit",  # OpenAI / 通用
    "too many requests",
    "quota",
    "quota exceeded",
    "api quota exceeded",
    "limit reached",
    "throttled",
    "rate limiting",
    "error-code-429",
]


def is_rate_limit_text(text: str) -> bool:
    """
    判断文本内容是否包含速率限制/限流错误信号。

    用于检测 API 返回的文本形式错误消息（而非异常对象）。

    Args:
        text: 待检测的文本内容

    Returns:
        如果文本包含速率限制相关的关键词或 429 状态码，返回 True
    """
    if not text:
        return False

    text_lower = text.lower()

    if any(k in text_lower for k in _RATE_LIMIT_KEYWORDS):
        return True

    if re.search(r"\b429\b", text_lower):
        return True

    return False


def is_rate_limit_error(error: Exception) -> bool:
    """
    判断是否为速率限制/限流错误（通常是 HTTP 429 或配额耗尽）。

    覆盖场景：
    - 文本错误信息包含 resource exhausted / rate limit / too many requests / quota 等
    - 异常对象或其 response 携带 status_code == 429
    - 异常链 __cause__ 里包含上述信号
    """
    error_msg = str(error).lower()

    if any(k in error_msg for k in _RATE_LIMIT_KEYWORDS):
        return True

    if re.search(r"\b429\b", error_msg):
        return True

    status_code = getattr(error, "status_code", None)
    if status_code == 429:
        return True

    response: Any = getattr(error, "response", None)
    if response is not None:
        resp_code = getattr(response, "status_code", None)
        if resp_code == 429:
            return True
        resp_text = getattr(response, "text", None)
        if resp_text:
            resp_text_l = str(resp_text).lower()
            if any(k in resp_text_l for k in _RATE_LIMIT_KEYWORDS) or re.search(r"\b429\b", resp_text_l):
                return True

    cause = getattr(error, "__cause__", None)
    if cause:
        return is_rate_limit_error(cause)

    return False
