# 根目录文件归类重构执行方案

## 1. 目标与约束
- 根目录仅保留运行入口（`main.py`、批处理脚本）、关键说明文档（`AGENTS.md`、`CLAUDE.md`、`README.md`）、以及仍需默认读取的配置文件（`config.json`、`config.example.json`、`prompts_config.json`）。
- 现有代码逻辑、导入路径与运行流程在重构完成后必须保持一致；所有迁移都需同步更新引用。
- 规划阶段不直接改动代码，本文档用于指导后续实际实施，需覆盖路径调整、依赖更新和验证步骤。

## 2. 根目录保留清单
- 隐藏配置：`.gitignore`、`.gitattributes`
- 运行入口：`main.py`、`run_gui.bat`
- 说明文档：`README.md`、`AGENTS.md`、`CLAUDE.md`
- 依赖/配置：`requirements.txt`、`config.json`、`config.example.json`、`prompts_config.json`
- 其余文件全部迁移至分类目录或下游模块内部。

## 3. 拟新增目录结构
| 目录 | 职责 | 备注 |
| --- | --- | --- |
| `core/` | 统一放置跨模块核心逻辑（配置、适配器、提示词、通用工具） | 需添加 `__init__.py` 构建包结构 |
| `core/adapters/` | LLM/Embedding 适配器模块 | 承载 `llm_adapters.py`、`embedding_adapters.py` |
| `core/config/` | 配置加载与校验逻辑 | 承载 `config_manager.py` 等 |
| `core/prompting/` | Prompt 管理相关模块 | 承载 `prompt_manager.py`、`prompt_manager_helper.py`、`prompt_definitions.py` |
| `core/utils/` | 通用工具与体量较大的辅助函数 | 承载 `utils.py`、`volume_utils.py`、`chapter_directory_parser.py` |
| `core/consistency/` | 剧情一致性校验 | 承载 `consistency_checker.py` |
| `scripts/maintenance/` | 运维/批处理脚本 | `add_dependencies.py`、`init_custom_prompts.py` 等 |
| `scripts/setup/` | 环境预设脚本 | `nltk_setup.py` 等 |
| `assets/` | 静态资源 | `icon.ico` 等 |
| `legacy/` | 历史兼容/弃用配置 | `global_prompt.json` 系列 |
| `tests/` | 自动化/手动测试脚本（已有目录需扩充） | 迁移 `test_*` 文件 |
| `logs/` | 运行期日志输出目录 | 之后在日志初始化中将路径指向此目录 |
| `packaging/` | 打包配置 | 存放 `main.spec` 等 |

## 4. 文件迁移明细

### 4.1 核心逻辑模块
| 当前路径 | 目标路径 | 受影响的引用（需更新为新包路径） | 附注 |
| --- | --- | --- | --- |
| `config_manager.py` | `core/config/config_manager.py` | `ui/config_tab.py`、`ui/other_settings.py`、`ui/main_window.py`、`ui/settings_tab.py`、`README.md` 等文档描述 | 需创建 `core/__init__.py`、`core/config/__init__.py`；引用改为 `from core.config.config_manager import ...` |
| `llm_adapters.py` | `core/adapters/llm_adapters.py` | `core/config/config_manager.py`、`core/consistency/consistency_checker.py`、`novel_generator/architecture.py`、`novel_generator/blueprint.py`、`novel_generator/chapter.py`、`novel_generator/finalization.py`、`ui/main_window.py` | 文档引用同步更新；注意迁移后在 `config_manager.py` 内部改用新路径 |
| `embedding_adapters.py` | `core/adapters/embedding_adapters.py` | `core/config/config_manager.py`、`novel_generator/chapter.py`、`novel_generator/finalization.py`、`novel_generator/knowledge.py`、`novel_generator/vectorstore_utils.py` | 同步更新导入路径及相关文档说明 |
| `prompt_definitions.py` | `core/prompting/prompt_definitions.py` | `core/prompting/prompt_manager.py`、`scripts/maintenance/init_custom_prompts.py`、`novel_generator/architecture.py`、`novel_generator/blueprint.py`、`novel_generator/chapter.py`、`novel_generator/finalization.py`、`ui/generation_handlers.py`、`ui/main_window.py`、`ui/role_library.py`、相关文档 | 在 `core/prompting/__init__.py` 提供必要导出 |
| `prompt_manager.py` | `core/prompting/prompt_manager.py` | `novel_generator/*`、`core/prompting/prompt_definitions.py`、`core/prompting/prompt_manager_helper.py`、`ui/prompt_manager_tab.py`、`test_prompt_manager.py` | 统一改为 `from core.prompting.prompt_manager import ...` |
| `prompt_manager_helper.py` | `core/prompting/prompt_manager_helper.py` | 文档、后续代码示例 | 建议在 `core/prompting/__init__.py` 中暴露便捷函数 |
| `chapter_directory_parser.py` | `core/utils/chapter_directory_parser.py` | `novel_generator/chapter.py`（含动态导入） | `core/utils/__init__.py` 导出必要函数 |
| `utils.py` | `core/utils/file_utils.py`（或保持文件名为 `core/utils/io_utils.py`） | `novel_generator/*`、`novel_generator/vectorstore_utils.py`、`ui/*` 多文件 | 统一改用 `from core.utils.file_utils import ...`，并更新 README 目录示意 |
| `volume_utils.py` | `core/utils/volume_utils.py` | `novel_generator/architecture.py`、`novel_generator/blueprint.py`、`novel_generator/chapter.py`、`novel_generator/finalization.py`、`novel_generator/vectorstore_utils.py`、`ui/main_window.py` | 与 `core/utils/__init__.py` 协同导出 |
| `consistency_checker.py` | `core/consistency/consistency_checker.py` | `ui/generation_handlers.py` | 创建 `core/consistency/__init__.py` 并更新导入 |

### 4.2 脚本与辅助工具
| 当前路径 | 目标路径 | 受影响的引用 | 附注 |
| --- | --- | --- | --- |
| `add_dependencies.py` | `scripts/maintenance/add_dependencies.py` | 文档/开发操作手册 | 更新 README“开发工具”章节 |
| `init_custom_prompts.py` | `scripts/maintenance/init_custom_prompts.py` | 文档或外部调用脚本 | 如通过命令行调用需在文档中注明新路径 |
| `nltk_setup.py` | `scripts/setup/nltk_setup.py` | 环境部署文档 | 如 README 提及需同步更新 |
| `test_config_lock.py` | `tests/manual/test_config_lock.py` | 脚本内部 `sys.path` 设置、README 提及的测试指引 | 调整为 `Path(__file__).resolve().parents[2]` 以定位项目根 |
| `test_prompt_manager.py` | `tests/manual/test_prompt_manager.py` | 脚本内部导入 `PromptManager` | 更新导入为 `from core.prompting.prompt_manager import PromptManager` |
| `tooltips.py` | `ui/common/tooltips.py` | `ui/config_tab.py`、`ui/novel_params_tab.py`、`ui/main_window.py` 等 | 新建 `ui/common/__init__.py` 并更新导入 |

### 4.3 静态资源与构建文件
| 当前路径 | 目标路径 | 受影响引用 | 附注 |
| --- | --- | --- | --- |
| `icon.ico` | `assets/icons/app.ico` | `ui/main_window.py`、`packaging/main.spec` | 使用 `Path` 组合资源路径，确保打包可找到资源 |
| `main.spec` | `packaging/main.spec` | 打包脚本/README | 更新 `Analysis` 中的源路径、图标路径 |
| `app.log`（运行产物） | `logs/app.log` | `novel_generator/*` 中多个 `logging.basicConfig`、文档描述 | 修改为 `logs/app.log` 并在初始化时确保目录存在；更新 README、AGENTS、CLAUDE 中的日志说明 |

### 4.4 文档与遗留配置
| 当前路径 | 目标路径 | 需要更新的引用 | 附注 |
| --- | --- | --- | --- |
| `FIXES_SUMMARY.md`、`PROMPT_MANAGER_GUIDE.md`、`CRITICAL_FIXES_REPORT.md` 等 | `docs/reports/`、`docs/guides/` | README、CLAUDE、AGENTS、Docs 内部互链 | 根据主题归档；目录树需同步调整 |
| `global_prompt.json`、`global_prompt.example.json` | `legacy/prompts/global_prompt.json` 等 | 文档关于旧 System Prompt 的说明 | 在文档中注明“仅保留历史备查，不再默认读取” |

## 5. 代码引用调整清单
- **UI 层**：`ui/config_tab.py`、`ui/other_settings.py`、`ui/main_window.py`、`ui/settings_tab.py`、`ui/novel_params_tab.py`、`ui/prompt_manager_tab.py`、`ui/generation_handlers.py`、`ui/role_library.py`、`ui/common/*` 等需更新导入路径。
- **生成引擎**：`novel_generator/architecture.py`、`novel_generator/blueprint.py`、`novel_generator/chapter.py`、`novel_generator/finalization.py`、`novel_generator/knowledge.py`、`novel_generator/vectorstore_utils.py` 等同步替换为新的 `core.*` 导入。
- **配置与适配器**：迁移后的 `core/config/config_manager.py` 须改用 `from core.adapters.llm_adapters import ...`、`from core.adapters.embedding_adapters import ...` 等新路径。
- **测试与脚本**：所有 `tests/manual/*.py` 与 `scripts/maintenance/*.py` 按新包结构调整导入；必要时添加 `sys.path` 处理确保独立运行。
- **文档**：README/CLAUDE/AGENTS 目录结构示意、执行指南及提示词管理设计文档需重新校对文件路径。

## 6. 执行步骤建议
1. **创建工作分支**：`git checkout -b chore/restructure-root`。
2. **创建目录骨架**：先行 `mkdir core core/adapters core/config core/prompting core/utils core/consistency scripts scripts/maintenance scripts/setup assets assets/icons legacy legacy/prompts logs packaging tests/manual`，为每个 Python 包目录添加 `__init__.py`。
3. **按类别迁移文件**：使用 `git mv` 保护历史记录。每迁移一个批次立即修正对应模块导入并运行格式化/静态检查。
4. **更新日志路径**：在所有 `logging.basicConfig` 调用处改为 `logs/app.log`，并在首次写入前 `logs_path.mkdir(exist_ok=True)`。
5. **修订文档与说明**：
   - README“项目结构”“开发者指南”章节
   - CLAUDE/AGENTS 中的根目录描述
   - 各种设计文档内的源码路径引用
6. **验证流程**：
   - `python -m compileall .` 或现有静态检查
   - `python main.py` 手动回归关键流程（架构生成→蓝图→章节→定稿）
   - 运行关键脚本（如 `scripts/maintenance/init_custom_prompts.py`）验证路径
   - 可选：`pytest` 或 `tests/manual/test_prompt_manager.py`
7. **收尾**：在 `.gitignore` 中加入 `logs/`（若需），确认根目录文件满足保留清单，更新 README 中的目录树示意后提交。

## 7. 风险与回滚
- **导入遗漏**：迁移后若出现 `ModuleNotFoundError`，使用 `rg "from core"` 检查替换情况或一键回滚相关提交。
- **循环依赖**：按“utils → prompting → 上层模块”的依赖层次编排，避免在 `core/prompting` 中再次引用 `core/utils` 外的高层模块。
- **日志路径问题**：若新日志目录不可写需提供回退策略（例如保留环境变量覆写能力）。
- **打包失败**：调整 `packaging/main.spec` 后若 PyInstaller 报错，可先回退至旧文件，逐项验证资源收集路径。

## 8. 后续交付
- 本规划文档：`ROOT_RESTRUCTURE_PLAN.md`
- 实施阶段需产出：
  - 新的目录结构及 `__init__.py`
  - 更新后的导入路径与文档
  - （可选）新增的路径验证自动化测试
- 建议实施完成后记录迁移脚本或指南，供后续贡献者参考。
