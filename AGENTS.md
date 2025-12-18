# Repository Guidelines
请务必使用中文与用户进行交流。

## 项目结构与模块组织
本仓库围绕 `core/`、`novel_generator/` 与 `ui/` 三大目录展开：`core/` 汇聚配置加载（`core/config/config_manager.py`）、LLM/Embedding 适配器、提示词管理与通用工具；`novel_generator/` 封装小说架构、章节蓝图、章节生成与定稿等核心流程；`ui/` 负责 CustomTkinter 图形界面、按钮事件与线程调度。运行时生成的 `Novel_architecture.txt`、`character_state.txt` 等产物仍会写入主界面选择的保存目录。

## 构建、测试与开发命令
1. `python -m venv venv` 创建隔离虚拟环境，`pip install -r requirements.txt` 安装依赖。
2. `python main.py` 启动 GUI；若在命令行调试，可关注 `logs/app.log` 了解后台进度。
3. 当前没有内建自动化测试；若新增测试，建议在 `tests/` 目录使用 `python -m pytest` 运行。

## 编码风格与命名约定
代码主要遵循 PEP 8：四空格缩进、`snake_case` 函数变量命名、类使用 `CapWords`。日志输出统一写入 `logs/app.log`，请复用 `logging` 与 `safe_log` 辅助方法，避免在 GUI 线程中直接操作控件。新文件保持 UTF-8 编码与中文用户界面文案一致。

## 测试准则
新增功能时优先编写对应的单元测试或集成测试，建议使用 `pytest` 并保持测试命名以 `test_` 开头。模拟 LLM 调用时，可使用本地桩对象或设置短超时时间，以免在 CI 卡住。提交前运行全部测试并记录关键场景（例如部分生成流程、异常重试）。

## 提交与 Pull Request 指南
提交信息建议采用简洁的祈使句，如 “Add chapter blueprint retry logging”。Pull Request 请包含：变更概述、涉及的配置说明、截图或日志片段（若 UI 或生成流程发生变化），以及需要关注的回归风险。若改动影响生成目录结构，请在描述中明确迁移步骤，提醒评审者同步验证。

## 配置与安全提示
敏感密钥应通过 `config.json` 或环境变量注入，避免硬编码在仓库中。为不同的 LLM 服务配置 `interface_format`、`base_url`、`timeout` 等参数时，请保留说明注释，便于贡献者快速复现。调试第三方接口时可设置代理，但请在 PR 中说明是否有外部依赖。
