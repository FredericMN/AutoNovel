# -*- coding: utf-8 -*-
"""
NLTK 资源自检与自动下载。
- 强依赖 punkt / punkt_tab，用于 nltk.sent_tokenize。
- 在程序启动和需要分句时调用，若缺失则尝试下载。
"""
import logging

def ensure_nltk_punkt_resources():
    """确保 nltk 的 punkt 和 punkt_tab 资源可用；若缺失则自动下载。
    若下载失败则抛出异常，由上层捕获并提示用户检查网络/代理。
    """
    try:
        import nltk
        from nltk.data import find
        # punkt
        try:
            find('tokenizers/punkt')
        except LookupError:
            logging.info('NLTK resource punkt not found. Downloading...')
            nltk.download('punkt', quiet=True)
            # 验证
            find('tokenizers/punkt')
        # punkt_tab（在较新版本NLTK中使用）
        try:
            find('tokenizers/punkt_tab')
        except LookupError:
            logging.info('NLTK resource punkt_tab not found. Downloading...')
            try:
                nltk.download('punkt_tab', quiet=True)
                find('tokenizers/punkt_tab')
            except Exception as e:
                # 兼容旧版本NLTK：若无 punkt_tab 包，记录警告但不抛出
                logging.warning(f'NLTK punkt_tab not available to download: {e}')
    except Exception as e:
        # 统一向外抛出，让调用方给出更直观的提示
        raise RuntimeError(f'Failed to ensure NLTK punkt resources: {e}')

