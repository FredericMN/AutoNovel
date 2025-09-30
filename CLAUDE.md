# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 沟通语言
请务必使用中文与用户进行交流。

## 项目概述
AutoNovel 是一个基于大语言模型的自动小说生成工具,支持多种 LLM 提供商(OpenAI、DeepSeek、Gemini、Azure 等)和本地向量检索。通过四个主要步骤生成长篇小说:
1. 生成设定(Novel_architecture.txt)
2. 生成目录(Novel_directory.txt)
3. 生成章节草稿(chapter_X.txt + outline_X.txt)
4. 定稿章节(更新 global_summary.txt、character_state.txt、向量库)

## 核心架构

### novel_generator/ - 核心生成逻辑
- **architecture.py**: 小说总体架构生成(世界观、角色、剧情雷点)
- **blueprint.py**: 章节蓝图/目录生成,支持分块处理大量章节
- **chapter.py**: 章节草稿生成,包含向量检索历史剧情
- **finalization.py**: 定稿章节,更新全局摘要和角色状态
- **vectorstore_utils.py**: 向量库操作(Chroma + LangChain),用于语义检索保证上下文一致性
- **knowledge.py**: 外部知识库导入支持

### ui/ - CustomTkinter 图形界面
- **main_window.py**: 主窗口和应用入口
- **generation_handlers.py**: 所有生成操作的 UI 线程处理逻辑
- **config_tab.py**: LLM 和 Embedding 配置界面
- **main_tab.py**: 主操作面板(四步生成流程)
- **chapters_tab.py**: 章节预览和编辑
- **character_tab.py**: 角色库管理
- **role_library.py**: 角色设定模板

### 根目录核心文件
- **llm_adapters.py**: 统一 LLM 接口适配器(OpenAI、Gemini、Azure 等),使用 LangChain
- **embedding_adapters.py**: Embedding 模型适配器(支持本地 Ollama 和云端服务)
- **prompt_definitions.py**: 所有提示词定义,包含雪花写作法、角色弧光理论等
- **config_manager.py**: 配置加载/保存/测试逻辑
- **consistency_checker.py**: 剧情一致性检查
- **chapter_directory_parser.py**: 解析 Novel_directory.txt 获取章节信息

## 常用命令

### 环境设置
```bash
python -m venv venv
pip install -r requirements.txt
```

### 运行应用
```bash
python main.py  # 启动 GUI
```

### 日志查看
生成过程中所有日志写入 `app.log`,可实时查看后台进度和错误。

### 打包为可执行文件
```bash
pip install pyinstaller
pyinstaller main.spec  # 生成 dist/main.exe
```

## 配置文件说明

### config.json 结构
- **llm_configs**: 多个 LLM 配置(DeepSeek、GPT、Gemini 等),每个包含 api_key、base_url、model_name、temperature、max_tokens、timeout、interface_format
- **embedding_configs**: Embedding 模型配置,支持 OpenAI 和 Ollama
- **choose_configs**: 为不同任务指定使用哪个 LLM(架构生成、蓝图生成、草稿生成、定稿、一致性检查)
- **other_params**: 小说参数(topic、genre、num_chapters、word_number、filepath 等)
- **proxy_setting**: 可选的代理配置
- **webdav_config**: WebDAV 同步配置(可选)

### global_prompt.json
全局 system prompt,可通过界面开关控制是否注入到所有 LLM 调用中。

## 关键技术细节

### 向量检索流程
1. 定稿章节时,使用 `update_vector_store()` 将章节文本切分并存入 Chroma
2. 生成新章节时,使用 `get_relevant_context_from_vector_store()` 检索相关历史片段
3. 切换 Embedding 模型后需清空 `vectorstore/` 目录

### LLM 适配器注册
- `llm_adapters.py` 的 `create_llm_adapter()` 根据 interface_format 创建对应适配器
- 所有适配器继承 `BaseLLMAdapter`,实现 `invoke(prompt, system_prompt)` 方法
- base_url 处理规则:以 `#` 结尾则不添加 `/v1`,否则自动补充

### 章节蓝图分块逻辑
`blueprint.py` 的 `compute_chunk_size()` 基于 `max_tokens` 动态计算每次生成的章节数,避免超出上下文窗口。

### 提示词系统
`prompt_definitions.py` 包含所有提示词:
- 架构生成: `core_seed_prompt`、`world_building_prompt`、`plot_architecture_prompt`
- 蓝图生成: `chapter_blueprint_prompt`、`chunked_chapter_blueprint_prompt`
- 章节生成: `first_chapter_draft_prompt`、`next_chapter_draft_prompt`
- 定稿: `summary_prompt`、`update_character_state_prompt`

### 全局 System Prompt
通过 `resolve_global_system_prompt(enabled)` 控制是否注入全局 system prompt。

## 编码规范
- 遵循 PEP 8: 四空格缩进、snake_case 函数变量命名、CapWords 类命名
- 所有文件 UTF-8 编码
- 日志使用 `logging` 模块写入 `app.log`
- GUI 操作必须通过 `threading` 避免阻塞主线程
- 敏感信息通过 `config.json` 配置,不硬编码

## 常见问题排查
- **"Expecting value: line 1 column 1"**: API 响应非 JSON,检查 api_key 和 base_url 是否正确
- **504 Gateway Timeout**: 接口不稳定或 timeout 设置过短
- **向量检索失败**: 确认 Embedding 配置正确,本地 Ollama 需先启动服务(`ollama serve`)
- **章节生成中断**: 查看 `app.log` 日志定位错误,可能是 token 不足或 API 限流

## 生成流程输出文件
所有文件保存在用户指定的 `filepath` 目录:
- `Novel_architecture.txt`: 世界观、角色、剧情架构
- `Novel_directory.txt`: 所有章节的标题和大纲
- `chapter_X.txt`: 第 X 章正文
- `outline_X.txt`: 第 X 章大纲
- `global_summary.txt`: 全局摘要
- `character_state.txt`: 角色状态变化
- `plot_arcs.txt`: 剧情要点
- `vectorstore/`: Chroma 向量数据库存储