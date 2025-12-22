# -*- coding: utf-8 -*-
"""跨平台工具函数。"""

import logging
import os
import subprocess
import sys
from pathlib import Path
import webbrowser


def open_path(path: str) -> bool:
    """跨平台打开文件或目录。"""
    if not path:
        return False

    target = Path(path)
    try:
        if sys.platform.startswith("win"):
            os.startfile(target)  # type: ignore[attr-defined]
            return True

        if sys.platform == "darwin":
            result = subprocess.run(["open", str(target)], check=False)
        else:
            result = subprocess.run(["xdg-open", str(target)], check=False)

        if result.returncode == 0:
            return True
        raise RuntimeError("open command failed")
    except Exception:
        logging.exception("打开路径失败: %s", path)
        if sys.platform == "darwin":
            return False
        try:
            if target.exists():
                return webbrowser.open(target.resolve().as_uri())
        except Exception:
            logging.exception("打开路径回退失败: %s", path)
        return False
