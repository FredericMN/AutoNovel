# main.py
# -*- coding: utf-8 -*-
import customtkinter as ctk
from ui import NovelGeneratorGUI
from scripts.setup.nltk_setup import ensure_nltk_punkt_resources

def main():
    app = ctk.CTk()
    gui = NovelGeneratorGUI(app)

    # 在GUI初始化后调用，确保代理设置已生效，再下载NLTK资源
    try:
        ensure_nltk_punkt_resources()
    except Exception as e:
        # 不阻断GUI启动；在定稿时仍会再次检测并提示
        import logging
        logging.warning(f"Ensure NLTK resources at startup failed: {e}")

    app.mainloop()

if __name__ == "__main__":
    main()


