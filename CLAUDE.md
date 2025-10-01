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
- **main_window.py**: 主窗口和应用入口（已应用iOS风格）
- **generation_handlers.py**: 所有生成操作的 UI 线程处理逻辑
- **config_tab.py**: LLM 和 Embedding 配置界面
- **main_tab.py**: 主操作面板(主界面页签,已应用iOS风格)
- **setting_tab.py**: 小说架构查看/编辑(Novel_architecture.txt)
- **volume_architecture_tab.py**: 分卷架构查看/编辑(Volume_architecture.txt)
- **directory_tab.py**: 目录蓝图查看/编辑(Novel_directory.txt)
- **character_tab.py**: 角色状态查看/编辑(character_state.txt)
- **summary_tab.py**: 全局概要查看/编辑(global_summary.txt)
- **volume_summary_tab.py**: 分卷概要查看/编辑(volume_X_summary.txt,支持多卷分页)
- **chapters_tab.py**: 章节管理(章节预览和编辑)
- **settings_tab.py**: 设置页签(所有配置项)
- **role_library.py**: 角色设定模板
- **ios_theme.py**: iOS风格主题配置（颜色、字体、布局参数）
- **ios_theme_helper.py**: iOS风格应用辅助工具（快速应用样式的工具函数）

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
# ⚠️ 重要：请勿直接运行 python main.py 测试GUI
# 应使用虚拟环境启动脚本测试前端功能
D:\project\AutoNovel\run_gui.bat
```

**测试说明**：
- 直接运行 `python main.py` 可能因缺少依赖导致失败
- 项目已配置虚拟环境和依赖，使用 `run_gui.bat` 启动即可
- 如需验证GUI功能，请调用 `run_gui.bat` 启动测试

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

### prompts_config.json
提示词模块配置文件，控制各个提示词模块的启用状态和自定义内容路径。

### 全局 System Prompt
全局系统提示词现已集成到提示词管理系统中：
- **配置位置**: 提示词管理页签 → 辅助功能 → 全局System Prompt
- **存储文件**: `custom_prompts/system_prompt.txt`
- **开关控制**: 通过 `prompts_config.json` 中的 `modules.helper.global_system.enabled` 控制
- **使用方式**: 在提示词管理页签中编辑和保存，所有 LLM 调用自动注入

## 关键技术细节

### 向量检索流程
1. 定稿章节时,使用 `update_vector_store()` 将章节文本切分并存入 Chroma,附带章节号和卷号元数据
2. 生成新章节时,使用 `get_relevant_contexts_deduplicated()` 检索相关历史片段
3. 切换 Embedding 模型后需清空 `vectorstore/` 目录
4. **跨卷检索增强**: 检测到关键词(如"起源"、"身世"、"预言"等)时,自动检索历史卷的相关内容
5. **卷摘要向量化**: 完成一卷后,将卷摘要也存入向量库,便于跨卷语义检索

### 分卷模式摘要传递策略
**当前策略**: 固定传递"上一卷完整摘要 + 本卷累积摘要" (2025-10-01 更新)

**传递逻辑** (`chapter.py:900-916`):
- **第一卷**: 仅使用 `global_summary.txt`(本卷累积)
- **第二卷及以后**:
  - 前置摘要 = `volume_{N-1}_summary.txt`(上一卷完整) + `global_summary.txt`(本卷累积)
  - 优势: 保证跨卷连贯性,避免丢失前一卷关键信息
  - 配合增强向量检索,可按需查找更早卷的具体内容

**卷摘要清空时机** (`finalization.py:177-180`):
- 每卷最后一章定稿后,生成 `volume_X_summary.txt`
- 清空 `global_summary.txt`,为下一卷重新累积摘要
- 卷摘要同时存入向量库,标记为卷号元数据

**跨卷检索策略** (`vectorstore_utils.py:328-377`):
1. 当前卷优先检索(占大部分结果)
2. 前一卷补充检索(1条)
3. 关键词触发历史卷检索(检测到"起源"、"身世"等词时,回溯最多3卷)

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
- **页签切换失效**: 如果页签无法切换,检查TabView的`command`参数是否被错误覆盖。应使用原生切换机制,不要自定义command回调

## 生成流程输出文件
所有文件保存在用户指定的 `filepath` 目录:
- `Novel_architecture.txt`: 世界观、角色、剧情架构
- `Volume_architecture.txt`: 分卷架构(仅分卷模式)
- `Novel_directory.txt`: 所有章节的标题和大纲
- `chapter_X.txt`: 第 X 章正文
- `outline_X.txt`: 第 X 章大纲
- `global_summary.txt`: 全局摘要
- `volume_X_summary.txt`: 第 X 卷摘要(仅分卷模式,可能多个)
- `character_state.txt`: 角色状态变化
- `plot_arcs.txt`: 剧情要点
- `vectorstore/`: Chroma 向量数据库存储

## 最新功能更新

### iOS风格UI优化 (2025-09-30)
项目UI已全面升级为iOS风格的现代简约设计：

**设计理念**：
- 参考Apple Human Interface Guidelines设计规范
- 简约、清晰、一致的视觉语言
- 舒适的留白和间距
- 流畅的圆角和阴影效果

**核心改进**：
1. **颜色方案**：
   - 主色调：iOS蓝 (#007AFF)
   - 背景色层级：
     - 应用底色：#E8E8ED（深灰）
     - 页签背景：#FAFAFA（极浅灰）
     - 卡片背景：#FFFFFF（纯白，带细微边框）
   - 文字色：黑色主文本 + 灰色次要文本
   - 状态色：绿色(成功)、橙色(警告)、红色(危险)

2. **布局优化**：
   - 所有内容区使用白色卡片容器（圆角16px + 细边框）
   - 统一的内边距系统（8/12/16/20px）
   - 主窗口尺寸：1680x920，提供更宽裕的视觉空间
   - 顶部添加边距，营造iOS风格的留白感
   - 三层背景色体系：应用底色 > 页签背景 > 卡片背景

3. **组件样式**：
   - 按钮：圆角12px，高度40px，iOS蓝色系
   - 输入框：圆角12px，白色背景，灰色边框
   - 文本框：圆角12px，白色背景，细边框，字体15px
   - 进度条：圆角设计，iOS蓝色进度
   - 标签：使用iOS风格字体大小和颜色层级

4. **导航栏优化**：
   - 高度增加到44px，视觉更突出
   - 字体增大到15px
   - 未选中项文字颜色优化为#3C3C43，提升可见度
   - 悬停效果更明显

5. **交互细节**：
   - 批量生成按钮：调整为柔和的绿色(#30B050)，降低视觉冲击
   - 保存状态指示器：使用Canvas绘制的彩色圆点替代emoji
     - 绿色圆点：已保存
     - 红色圆点：未保存
     - 橙色圆点：保存中
   - 文本编辑区字体：统一增大到15px，提升可读性
   - 页签切换：原生CustomTkinter切换机制，流畅稳定

6. **已优化页面**：
   - ✅ 主窗口（main_window.py）
   - ✅ 主界面页签（main_tab.py）- 包含三段式布局优化
   - ✅ 步骤按钮区域 - 应用主按钮样式
   - ✅ 批量生成按钮 - 使用柔和绿色按钮样式
   - ✅ 进度条区域 - 卡片式容器 + iOS风格进度条
   - ✅ 日志区域 - 卡片样式文本框
   - ✅ 保存状态指示器 - Canvas圆点替代emoji

**技术实现**：
- `ui/ios_theme.py`: 完整的iOS风格配置系统
  - `IOSColors`: 配色方案类（新增BG_CARD、BG_APP等）
  - `IOSLayout`: 布局参数类（圆角、间距、控件尺寸、TAB_HEIGHT、FONT_SIZE_EDITOR）
  - `IOSFonts`: 字体配置类
  - `IOSStyles`: 组件样式预设类
  - `apply_ios_theme()`: 主题应用函数
  - `create_card_frame()`: 创建白色卡片+细边框

- `ui/ios_theme_helper.py`: 快速应用工具
  - `create_ios_button()`: 创建iOS风格按钮
  - `create_ios_entry()`: 创建iOS风格输入框
  - `create_ios_textbox()`: 创建iOS风格文本框
  - `create_ios_label()`: 创建iOS风格标签
  - `build_standard_edit_tab()`: 标准编辑页签模板
  - `apply_ios_card_layout()`: 卡片式布局应用

- `ui/validation_utils.py`: 保存状态指示器优化
  - 使用`tk.Canvas`绘制彩色圆点
  - 避免Windows系统emoji显示问题

**视觉层级体系**：
```
应用窗口 (#E8E8ED 深灰)
 └─ 外边距 (16px)
    └─ TabView容器 (#FAFAFA 极浅灰)
       └─ 页签内容 (#FAFAFA)
          └─ 卡片容器 (#FFFFFF 纯白 + 细边框)
             └─ 内容区域
```

**如何应用到其他页签**：
```python
# 1. 导入主题
from ui.ios_theme_helper import build_standard_edit_tab

# 2. 使用预设模板快速构建（适用于简单编辑页签）
widgets = build_standard_edit_tab(
    parent_tab=self.your_tab,
    title="文件名.txt",
    load_callback=self.load_function,
    save_callback=self.save_function
)

# 3. 或手动应用样式
from ui.ios_theme import IOSStyles, IOSLayout, IOSColors
btn = ctk.CTkButton(parent, text="按钮", **IOSStyles.primary_button())
```

参考示例：`ui/setting_tab_ios_example.py`

### 分卷功能支持 (2025-09-30)
项目现已全面支持分卷模式，包含以下增强：

**后端功能**：
- 支持多卷小说生成，每卷独立架构和摘要
- 自动生成分卷架构文件 `Volume_architecture.txt`
- 为每卷生成独立摘要 `volume_X_summary.txt`

**前端功能**：
- 新增**分卷架构**页签：查看/编辑 `Volume_architecture.txt`
- 新增**分卷概要**页签：支持多卷切换查看，使用 `CTkSegmentedButton` 实现分卷选择器
- 所有页签已汉化：主界面、小说架构、分卷架构、目录蓝图、角色状态、全局概要、分卷概要、章节管理、设置

**页签布局顺序**：
1. 主界面 (Main Functions)
2. 小说架构 (Novel Architecture)
3. 分卷架构 (Volume Architecture) - 新增
4. 目录蓝图 (Chapter Blueprint)
5. 角色状态 (Character State)
6. 全局概要 (Global Summary)
7. 分卷概要 (Volume Summary) - 新增
8. 章节管理 (Chapters Manage)
9. 设置 (Settings)