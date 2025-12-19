# AutoNovel 项目指南

## 项目概述
**AutoNovel** 是一个基于大语言模型（LLM）的全流程长篇小说创作工具。它旨在解决长篇生成中的一致性问题，支持多卷架构、剧情伏笔管理（ABC分级）和基于 RAG（检索增强生成）的上下文记忆。项目采用 Python 编写，使用 CustomTkinter 构建现代化 GUI。

## 沟通语言
请务必使用中文与用户进行交流。

## 项目概述
AutoNovel 是一个基于大语言模型的自动小说生成工具，支持多种 LLM 提供商（OpenAI、DeepSeek、Gemini、Azure 等）和本地向量检索。通过四个主要步骤生成长篇小说：
1. 生成设定（Novel_architecture.txt）
2. 生成目录（Novel_directory.txt）
3. 生成章节草稿（chapter_X.txt + outline_X.txt）
4. 定稿章节（更新 global_summary.txt、character_state.txt、向量库）

## 常用命令

### 环境设置
```bash
python -m venv venv
pip install -r requirements.txt
```

### 运行应用
```bash
# Windows - 推荐使用启动脚本
D:\project\AutoNovel\run_gui.bat

# 或直接运行（需在虚拟环境中）
python main.py
```

### 日志查看
生成过程中所有日志写入 `logs/app.log`，可实时查看后台进度和错误。

### 打包为可执行文件
```bash
pip install pyinstaller
pyinstaller packaging/main.spec  # 生成 dist/main.exe
```

## 核心架构

### 项目目录结构
```
AutoNovel/
├── main.py                      # GUI 入口
├── core/                        # 核心基础组件
│   ├── adapters/                # LLM / Embedding 适配器
│   ├── config/                  # 配置加载与测试工具
│   ├── consistency/             # 剧情一致性校验
│   ├── prompting/               # 提示词管理与默认模板
│   └── utils/                   # 通用工具
├── novel_generator/             # 小说生成核心流程
│   ├── architecture.py          # 小说总体架构生成
│   ├── blueprint.py             # 章节蓝图/目录生成
│   ├── chapter.py               # 章节草稿生成
│   ├── finalization.py          # 定稿章节
│   ├── vectorstore_utils.py     # 向量库操作
│   └── knowledge.py             # 外部知识库导入
├── ui/                          # CustomTkinter 图形界面
│   ├── main_window.py           # 主窗口（已应用iOS风格）
│   ├── generation_handlers.py   # 生成操作的 UI 线程处理
│   ├── ios_theme.py             # iOS风格主题配置
│   └── ...                      # 各功能页签
├── custom_prompts/              # 自定义提示词文件
├── scripts/                     # 辅助脚本
├── packaging/                   # 打包配置
└── tests/                       # 测试脚本
```

### novel_generator/ - 核心生成逻辑
- **architecture.py**: 小说总体架构生成（世界观、角色、剧情雷点）
- **blueprint.py**: 章节蓝图/目录生成，支持分块处理大量章节
- **chapter.py**: 章节草稿生成，包含向量检索历史剧情
- **finalization.py**: 定稿章节，更新全局摘要和角色状态
- **vectorstore_utils.py**: 向量库操作（Chroma + LangChain）

### core/ - 基础组件
- **adapters/llm_adapters.py**: 统一 LLM 接口适配器（OpenAI、Gemini、Azure 等）
- **adapters/embedding_adapters.py**: Embedding 模型适配器
- **prompting/prompt_definitions.py**: 所有提示词定义，包含雪花写作法、角色弧光理论等
- **prompting/prompt_manager.py**: 提示词管理入口
- **config/config_manager.py**: 配置加载/保存/测试逻辑
- **utils/volume_utils.py**: 分卷相关工具函数

### ui/ - 图形界面模块
- **main_window.py**: 主窗口和应用入口
- **generation_handlers.py**: 所有生成操作的 UI 线程处理逻辑
- **ios_theme.py**: iOS风格主题配置（颜色、字体、布局参数）

## 关键技术细节

### 向量检索流程
1. 定稿章节时，使用 `update_vector_store()` 将章节文本切分并存入 Chroma
2. 生成新章节时，使用 `get_relevant_contexts_deduplicated()` 检索相关历史片段
3. 切换 Embedding 模型后需清空 `vectorstore/` 目录
4. **跨卷检索增强**: 检测到关键词时，自动检索历史卷的相关内容

### 分卷模式摘要传递策略
- **第一卷**: 仅使用 `global_summary.txt`（本卷累积）
- **第二卷及以后**: 前置摘要 = `volume_{N-1}_summary.txt`（上一卷完整） + `global_summary.txt`（本卷累积）
- 每卷最后一章定稿后，生成 `volume_X_summary.txt`，清空 `global_summary.txt`

### LLM 适配器注册
- `core/adapters/llm_adapters.py` 的 `create_llm_adapter()` 根据 interface_format 创建对应适配器
- 所有适配器继承 `BaseLLMAdapter`，实现 `invoke(prompt, system_prompt)` 方法
- base_url 处理规则：以 `#` 结尾则不添加 `/v1`，否则自动补充

### 章节蓝图分块逻辑
`blueprint.py` 的 `compute_chunk_size()` 基于 `max_tokens` 动态计算每次生成的章节数。

### 剧情要点管理系统
- **双版本管理**: 详细版(`plot_arcs.txt`) + 精简版(融入摘要)
- **ABC分级**: [A级-主线]、[B级-支线]、[C级-细节]
- **智能压缩**: 每10章自动触发，A级≤30条，B级≤10条，C级≤3条
- **定稿流程**: 步骤2.5更新剧情要点 → 步骤2.6智能压缩 → 步骤2.8提炼到摘要

## 配置文件说明

### config.json 结构
- **llm_configs**: 多个 LLM 配置（每个包含 api_key、base_url、model_name、temperature、max_tokens、timeout、interface_format）
- **embedding_configs**: Embedding 模型配置
- **choose_configs**: 为不同任务指定使用哪个 LLM
- **other_params**: 小说参数（topic、genre、num_chapters、word_number、filepath 等）

### prompts_config.json
提示词模块配置文件，控制各个提示词模块的启用状态和自定义内容路径。

## 编码规范
- 遵循 PEP 8：四空格缩进、snake_case 函数变量命名、CapWords 类命名
- 所有文件 UTF-8 编码
- 日志使用 `logging` 模块写入 `logs/app.log`
- GUI 操作必须通过 `threading` 避免阻塞主线程

## 常见问题排查
- **"Expecting value: line 1 column 1"**: API 响应非 JSON，检查 api_key 和 base_url 是否正确
- **504 Gateway Timeout**: 接口不稳定或 timeout 设置过短
- **向量检索失败**: 确认 Embedding 配置正确，本地 Ollama 需先启动服务
- **章节生成中断**: 查看 `logs/app.log` 日志定位错误
- **页签切换失效**: 不要自定义 TabView 的 command 回调，使用原生切换机制

## 生成流程输出文件
所有文件保存在用户指定的 `filepath` 目录：
- `Novel_architecture.txt`: 世界观、角色、剧情架构
- `Volume_architecture.txt`: 分卷架构（仅分卷模式）
- `Novel_directory.txt`: 所有章节的标题和大纲
- `chapter_X.txt`: 第 X 章正文
- `outline_X.txt`: 第 X 章大纲
- `global_summary.txt`: 全局摘要
- `volume_X_summary.txt`: 第 X 卷摘要（仅分卷模式）
- `character_state.txt`: 角色状态变化
- `plot_arcs.txt`: 剧情要点
- `vectorstore/`: Chroma 向量数据库存储

