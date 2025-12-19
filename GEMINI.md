# AutoNovel 项目指南

## 项目概述
**AutoNovel** 是一个基于大语言模型（LLM）的全流程长篇小说创作工具。它旨在解决长篇生成中的一致性问题，支持多卷架构、剧情伏笔管理（ABC分级）和基于 RAG（检索增强生成）的上下文记忆。项目采用 Python 编写，使用 CustomTkinter 构建现代化 GUI。

## 目录结构
*   **`main.py`**: 应用程序入口点，启动 GUI。
*   **`config.example.json`**: 配置文件模板，包含 LLM API 密钥和模型参数。
*   **`prompts_config.json`**: 提示词模块配置，定义了各步骤使用的提示词文件和依赖变量。
*   **`core/`**: 核心基础设施。
    *   `adapters/`: LLM 和 Embedding 模型的适配器（支持 OpenAI, DeepSeek, Gemini, Azure, Ollama 等）。
    *   `config/`: 配置加载与验证逻辑。
    *   `prompting/`: 提示词管理器，负责加载和渲染 `custom_prompts/` 中的模板。
    *   `consistency/`: 剧情一致性检查模块。
*   **`novel_generator/`**: 核心业务逻辑。
    *   `architecture.py`: 生成世界观和架构。
    *   `blueprint.py`: 生成章节蓝图（大纲）。
    *   `chapter.py`: 章节正文生成逻辑（含向量检索集成）。
    *   `finalization.py`: 定稿处理（更新摘要、角色状态、伏笔）。
    *   `vectorstore_utils.py`: ChromaDB 向量库操作。
*   **`ui/`**: 用户界面模块（基于 CustomTkinter）。
    *   按功能拆分为多个 Tab 文件（如 `chapters_tab.py`, `character_tab.py`）。
    *   `ios_theme.py`: iOS 风格主题配置。
*   **`custom_prompts/`**: 存放 `.txt` 格式的提示词模板。

## 安装与运行

### 1. 环境准备
确保 Python 版本 >= 3.9。建议使用虚拟环境。

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows)
venv\Scripts\activate

# 激活虚拟环境 (macOS/Linux)
source venv/bin/activate
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```
*注意：在 macOS 上可能需要手动移除 `requirements.txt` 中的 `pyreadline3`。*

### 3. 配置文件
复制 `config.example.json` 为 `config.json` 并填写 API 密钥：
```bash
cp config.example.json config.json
```
在 `config.json` 中配置 `llm_configs` 和 `choose_configs` 以选择不同的模型处理不同的任务（如架构生成、章节撰写）。

### 4. 运行应用
```bash
python main.py
```

## 开发规范

### 代码风格
*   遵循 PEP 8 规范。
*   **类型提示 (Type Hints)**：核心模块（`core/`, `novel_generator/`）应广泛使用类型提示。
*   **模块化**：UI 代码与业务逻辑代码应保持分离。

### 核心机制
*   **提示词管理**：不要在代码中硬编码提示词。所有提示词应存放在 `custom_prompts/` 并在 `prompts_config.json` 中注册。
*   **多模型适配**：通过 `core.adapters.llm_adapters.BaseLLMAdapter` 扩展新的 LLM 支持。
*   **RAG 流程**：章节生成依赖于 ChromaDB 检索历史内容。在修改 `chapter.py` 时需注意上下文检索逻辑。

### 常见任务
*   **添加新模型**：在 `core/adapters/llm_adapters.py` 中实现新的 Adapter 类，并在 `create_llm_adapter` 工厂函数中注册。
*   **修改 UI**：在 `ui/` 目录下找到对应的 Tab 文件进行修改，样式请引用 `ui/ios_theme.py`。
*   **调整生成逻辑**：主要逻辑位于 `novel_generator/` 目录下的各模块中。
