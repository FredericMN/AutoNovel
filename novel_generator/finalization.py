#novel_generator/finalization.py
# -*- coding: utf-8 -*-
"""
定稿章节和扩写章节（finalize_chapter、enrich_chapter_text）
"""
import os
import logging
from llm_adapters import create_llm_adapter
from embedding_adapters import create_embedding_adapter
from prompt_definitions import summary_prompt, update_character_state_prompt, resolve_global_system_prompt
from novel_generator.common import invoke_with_cleaning
from utils import read_file, clear_file_content, save_string_to_txt
from novel_generator.vectorstore_utils import update_vector_store
logging.basicConfig(
    filename='app.log',      # 日志文件名
    filemode='a',            # 追加模式（'w' 会覆盖）
    level=logging.INFO,      # 记录 INFO 及以上级别的日志
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
def finalize_chapter(
    novel_number: int,
    word_number: int,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    filepath: str,
    embedding_api_key: str,
    embedding_url: str,
    embedding_interface_format: str,
    embedding_model_name: str,
    interface_format: str,
    max_tokens: int,
    timeout: int = 600,
    use_global_system_prompt: bool = False,
    gui_log_callback=None  # 新增GUI日志回调
):
    """
    对指定章节做最终处理：更新前文摘要、更新角色状态、插入向量库等。
    默认无需再做扩写操作，若有需要可在外部调用 enrich_chapter_text 处理后再定稿。
    """
    # GUI日志辅助函数
    def gui_log(msg):
        if gui_log_callback:
            gui_log_callback(msg)
        logging.info(msg)

    gui_log("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    gui_log(f"📝 开始定稿第{novel_number}章")
    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    chapters_dir = os.path.join(filepath, "chapters")
    chapter_file = os.path.join(chapters_dir, f"chapter_{novel_number}.txt")
    chapter_text = read_file(chapter_file).strip()
    if not chapter_text:
        gui_log("❌ 章节文件为空，无法定稿")
        logging.warning(f"Chapter {novel_number} is empty, cannot finalize.")
        return

    gui_log(f"▶ [1/3] 更新前文摘要")
    gui_log("   ├─ 读取旧摘要...")
    global_summary_file = os.path.join(filepath, "global_summary.txt")
    old_global_summary = read_file(global_summary_file)
    character_state_file = os.path.join(filepath, "character_state.txt")
    old_character_state = read_file(character_state_file)

    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )
    system_prompt = resolve_global_system_prompt(use_global_system_prompt)

    prompt_summary = summary_prompt.format(
        chapter_text=chapter_text,
        global_summary=old_global_summary
    )
    gui_log("   ├─ 向LLM发起请求...")
    new_global_summary = invoke_with_cleaning(llm_adapter, prompt_summary, system_prompt=system_prompt)
    if not new_global_summary.strip():
        gui_log("   ├─ ⚠ 生成失败，保留旧摘要")
        new_global_summary = old_global_summary
    else:
        gui_log("   └─ ✅ 前文摘要更新完成\n")

    gui_log("▶ [2/3] 更新角色状态")
    gui_log("   ├─ 读取旧状态...")
    prompt_char_state = update_character_state_prompt.format(
        chapter_text=chapter_text,
        old_state=old_character_state
    )
    gui_log("   ├─ 向LLM发起请求...")
    new_char_state = invoke_with_cleaning(llm_adapter, prompt_char_state, system_prompt=system_prompt)
    if not new_char_state.strip():
        gui_log("   ├─ ⚠ 生成失败，保留旧状态")
        new_char_state = old_character_state
    else:
        gui_log("   └─ ✅ 角色状态更新完成\n")

    gui_log("   ├─ 保存更新结果...")
    clear_file_content(global_summary_file)
    save_string_to_txt(new_global_summary, global_summary_file)
    clear_file_content(character_state_file)
    save_string_to_txt(new_char_state, character_state_file)

    gui_log("▶ [3/3] 插入向量库")
    gui_log("   ├─ 切分章节文本...")
    update_vector_store(
        embedding_adapter=create_embedding_adapter(
            embedding_interface_format,
            embedding_api_key,
            embedding_url,
            embedding_model_name
        ),
        new_chapter=chapter_text,
        filepath=filepath
    )
    gui_log("   └─ ✅ 向量库更新完成\n")

    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    gui_log(f"✅ 第{novel_number}章定稿完成")
    gui_log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logging.info(f"Chapter {novel_number} has been finalized.")

def enrich_chapter_text(
    chapter_text: str,
    word_number: int,
    api_key: str,
    base_url: str,
    model_name: str,
    temperature: float,
    interface_format: str,
    max_tokens: int,
    timeout: int = 600,
    use_global_system_prompt: bool = False
) -> str:
    """
    对章节文本进行扩写，使其更接近 word_number 字数，保持剧情连贯。
    """
    llm_adapter = create_llm_adapter(
        interface_format=interface_format,
        base_url=base_url,
        model_name=model_name,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout
    )
    system_prompt = resolve_global_system_prompt(use_global_system_prompt)
    prompt = f"""以下章节文本较短，请在保持剧情连贯的前提下进行扩写，使其更充实，接近 {word_number} 字左右，仅给出最终文本，不要解释任何内容。：
原内容：
{chapter_text}
"""
    enriched_text = invoke_with_cleaning(llm_adapter, prompt, system_prompt=system_prompt)
    return enriched_text if enriched_text else chapter_text
