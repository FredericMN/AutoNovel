# 提示词管理系统设计方案

## 📋 文档信息

- **版本**：1.0
- **创建日期**：2025-10-01
- **最后更新**：2025-10-01
- **状态**：待实施

---

## 🎯 一、设计目标

### 核心目标
1. **灵活可配置**：用户可选择启用/禁用各个提示词模块
2. **可编辑性**：用户可以在GUI中直接修改提示词内容
3. **统一管理**：将全局System Prompt纳入统一管理
4. **文件化存储**：自定义提示词存储为独立的txt文件
5. **向下兼容**：不影响现有功能，默认全部启用

### 用户价值
- 简化小说创作流程（简单小说可跳过世界观、三幕式等复杂模块）
- 提供更高的自定义自由度
- 降低复杂度和API调用成本
- 支持不同创作风格的提示词模板

---

## 📊 二、提示词模块清单

### 2.1 架构生成阶段（4个模块）

| 模块ID | 模块名称 | 提示词变量 | 是否必需 | 说明 |
|--------|---------|-----------|---------|------|
| `architecture.core_seed` | 核心种子 | `core_seed_prompt` | ✅ 必需 | 生成主题、类型、核心冲突 |
| `architecture.character_dynamics` | 角色动力学 | `character_dynamics_prompt` | ❌ 可选 | 角色设定与关系网 |
| `architecture.world_building` | 世界观构建 | `world_building_prompt` | ❌ 可选 | 世界观、设定、规则体系 |
| `architecture.plot_architecture` | 三幕式情节 | `plot_architecture_prompt` | ❌ 可选 | 情节架构（起承转合） |

**禁用行为**：跳过该步骤，在 `Novel_architecture.txt` 中标记"（已跳过xxx生成）"

### 2.2 目录生成阶段（3个模块）

| 模块ID | 模块名称 | 提示词变量 | 是否必需 |
|--------|---------|-----------|---------|
| `blueprint.chapter_blueprint` | 章节蓝图 | `chapter_blueprint_prompt` | ✅ 必需 |
| `blueprint.chunked_blueprint` | 分块蓝图 | `chunked_chapter_blueprint_prompt` | ✅ 必需 |
| `blueprint.volume_breakdown` | 分卷架构 | `volume_breakdown_prompt` | ❌ 可选 |

### 2.3 章节生成阶段（3个模块）

| 模块ID | 模块名称 | 提示词变量 | 是否必需 |
|--------|---------|-----------|---------|
| `chapter.first_chapter` | 第一章草稿 | `first_chapter_draft_prompt` | ✅ 必需 |
| `chapter.next_chapter` | 后续章节草稿 | `next_chapter_draft_prompt` | ✅ 必需 |
| `chapter.summary` | 当前章节摘要 | `summarize_recent_chapters_prompt` | ❌ 可选 |

### 2.4 定稿阶段（3个模块）

| 模块ID | 模块名称 | 提示词变量 | 是否必需 |
|--------|---------|-----------|---------|
| `finalization.summary_update` | 前文摘要更新 | `summary_prompt` | ❌ 可选 |
| `finalization.character_state_update` | 角色状态更新 | `update_character_state_prompt` | ❌ 可选 |
| `finalization.volume_summary` | 卷总结生成 | `volume_summary_prompt` | ❌ 可选 |

### 2.5 辅助功能（4个模块）

| 模块ID | 模块名称 | 提示词变量 | 是否必需 |
|--------|---------|-----------|---------|
| `helper.knowledge_search` | 知识库搜索 | `knowledge_search_prompt` | ❌ 可选 |
| `helper.knowledge_filter` | 知识库过滤 | `knowledge_filter_prompt` | ❌ 可选 |
| `helper.create_character_state` | 初始角色状态 | `create_character_state_prompt` | ❌ 可选 |
| `helper.global_system` | 全局System Prompt | `system_prompt` | ❌ 可选 |

**统计**：共17个模块（包含全局System Prompt），其中6个必需，11个可选

---

## 🗂️ 三、文件结构设计

### 3.1 配置文件：`prompts_config.json`

```json
{
  "_version": "1.0",
  "_description": "提示词模块配置文件",
  "_last_modified": "2025-10-01",

  "modules": {
    "architecture": {
      "core_seed": {
        "enabled": true,
        "required": true,
        "display_name": "核心种子生成",
        "description": "生成小说的核心主题、类型和冲突",
        "file": "custom_prompts/core_seed_prompt.txt"
      },
      "character_dynamics": {
        "enabled": true,
        "required": false,
        "display_name": "角色动力学",
        "description": "角色设定、性格、关系网络",
        "file": "custom_prompts/character_dynamics_prompt.txt"
      },
      "world_building": {
        "enabled": true,
        "required": false,
        "display_name": "世界观构建",
        "description": "世界观、背景设定、规则体系",
        "file": "custom_prompts/world_building_prompt.txt"
      },
      "plot_architecture": {
        "enabled": true,
        "required": false,
        "display_name": "三幕式情节",
        "description": "情节架构（起承转合）",
        "file": "custom_prompts/plot_architecture_prompt.txt"
      }
    },

    "blueprint": {
      "chapter_blueprint": {
        "enabled": true,
        "required": true,
        "display_name": "章节蓝图",
        "description": "生成所有章节的标题和大纲",
        "file": "custom_prompts/chapter_blueprint_prompt.txt"
      },
      "chunked_blueprint": {
        "enabled": true,
        "required": true,
        "display_name": "分块蓝图生成",
        "description": "分块生成大量章节的蓝图",
        "file": "custom_prompts/chunked_chapter_blueprint_prompt.txt"
      },
      "volume_breakdown": {
        "enabled": true,
        "required": false,
        "display_name": "分卷架构",
        "description": "分卷小说的卷架构规划",
        "file": "custom_prompts/volume_breakdown_prompt.txt"
      }
    },

    "chapter": {
      "first_chapter": {
        "enabled": true,
        "required": true,
        "display_name": "第一章草稿",
        "description": "生成第一章的草稿内容",
        "file": "custom_prompts/first_chapter_draft_prompt.txt"
      },
      "next_chapter": {
        "enabled": true,
        "required": true,
        "display_name": "后续章节草稿",
        "description": "生成第二章及以后的草稿内容",
        "file": "custom_prompts/next_chapter_draft_prompt.txt"
      },
      "summary": {
        "enabled": true,
        "required": false,
        "display_name": "章节摘要生成",
        "description": "生成当前章节的摘要",
        "file": "custom_prompts/summarize_recent_chapters_prompt.txt"
      }
    },

    "finalization": {
      "summary_update": {
        "enabled": true,
        "required": false,
        "display_name": "前文摘要更新",
        "description": "定稿时更新全局摘要",
        "file": "custom_prompts/summary_prompt.txt"
      },
      "character_state_update": {
        "enabled": true,
        "required": false,
        "display_name": "角色状态更新",
        "description": "定稿时更新角色状态表",
        "file": "custom_prompts/update_character_state_prompt.txt"
      },
      "volume_summary": {
        "enabled": true,
        "required": false,
        "display_name": "卷总结生成",
        "description": "生成每卷的总结",
        "file": "custom_prompts/volume_summary_prompt.txt"
      }
    },

    "helper": {
      "knowledge_search": {
        "enabled": true,
        "required": false,
        "display_name": "知识库搜索",
        "description": "从知识库中搜索相关内容",
        "file": "custom_prompts/knowledge_search_prompt.txt"
      },
      "knowledge_filter": {
        "enabled": true,
        "required": false,
        "display_name": "知识库过滤",
        "description": "过滤知识库搜索结果",
        "file": "custom_prompts/knowledge_filter_prompt.txt"
      },
      "create_character_state": {
        "enabled": true,
        "required": false,
        "display_name": "初始角色状态",
        "description": "创建初始角色状态表",
        "file": "custom_prompts/create_character_state_prompt.txt"
      },
      "global_system": {
        "enabled": false,
        "required": false,
        "display_name": "全局System Prompt",
        "description": "全局系统提示词（所有LLM调用都会注入）",
        "file": "custom_prompts/system_prompt.txt"
      }
    }
  }
}
```

### 3.2 自定义提示词文件结构

```
D:\project\AutoNovel\
├── custom_prompts/               # 自定义提示词目录
│   ├── system_prompt.txt         # 全局System Prompt
│   ├── core_seed_prompt.txt      # 核心种子
│   ├── character_dynamics_prompt.txt
│   ├── world_building_prompt.txt
│   ├── plot_architecture_prompt.txt
│   ├── chapter_blueprint_prompt.txt
│   ├── chunked_chapter_blueprint_prompt.txt
│   ├── volume_breakdown_prompt.txt
│   ├── first_chapter_draft_prompt.txt
│   ├── next_chapter_draft_prompt.txt
│   ├── summarize_recent_chapters_prompt.txt
│   ├── summary_prompt.txt
│   ├── update_character_state_prompt.txt
│   ├── volume_summary_prompt.txt
│   ├── knowledge_search_prompt.txt
│   ├── knowledge_filter_prompt.txt
│   └── create_character_state_prompt.txt
├── prompts_config.json           # 配置文件
└── prompt_manager.py             # 管理器类
```

**说明**：
- 如果 `custom_prompts/xxx.txt` 文件不存在，使用 `prompt_definitions.py` 中的默认值
- 如果文件存在但为空，也使用默认值
- 用户在GUI中编辑后，保存到对应的txt文件

---

## 🔧 四、技术实现方案

### 4.1 核心类：`PromptManager`

**文件路径**：`D:\project\AutoNovel\prompt_manager.py`

```python
# prompt_manager.py
# -*- coding: utf-8 -*-
"""
提示词管理器
负责加载、保存、管理所有提示词模块
"""
import json
import os
import logging
from typing import Dict, Optional

class PromptManager:
    """提示词管理器"""

    def __init__(self, config_path="prompts_config.json", custom_dir="custom_prompts"):
        self.config_path = config_path
        self.custom_dir = custom_dir
        self.config = self.load_config()
        self.default_prompts = self._load_default_prompts()

        # 确保自定义提示词目录存在
        os.makedirs(self.custom_dir, exist_ok=True)

    def load_config(self) -> dict:
        """加载配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Failed to load prompts_config.json: {e}")
                return self._create_default_config()
        return self._create_default_config()

    def _create_default_config(self) -> dict:
        """创建默认配置"""
        # 返回默认配置结构（省略具体内容）
        pass

    def _load_default_prompts(self) -> dict:
        """从 prompt_definitions.py 加载默认提示词"""
        from prompt_definitions import (
            core_seed_prompt, character_dynamics_prompt,
            world_building_prompt, plot_architecture_prompt,
            # ... 其他提示词
        )
        return {
            "core_seed_prompt": core_seed_prompt,
            "character_dynamics_prompt": character_dynamics_prompt,
            # ... 映射所有提示词
        }

    def is_module_enabled(self, category: str, name: str) -> bool:
        """检查模块是否启用"""
        try:
            return self.config["modules"][category][name]["enabled"]
        except KeyError:
            logging.warning(f"Module {category}.{name} not found in config")
            return True  # 默认启用

    def get_prompt(self, category: str, name: str) -> Optional[str]:
        """获取提示词（优先自定义，否则默认）"""
        try:
            module = self.config["modules"][category][name]
            file_path = module["file"]

            # 尝试读取自定义文件
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content:
                        return content

            # 否则返回默认值
            prompt_key = self._get_prompt_key(category, name)
            return self.default_prompts.get(prompt_key, "")

        except Exception as e:
            logging.error(f"Failed to get prompt {category}.{name}: {e}")
            return None

    def save_custom_prompt(self, category: str, name: str, content: str):
        """保存自定义提示词到文件"""
        try:
            module = self.config["modules"][category][name]
            file_path = module["file"]

            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logging.info(f"Saved custom prompt: {category}.{name}")
        except Exception as e:
            logging.error(f"Failed to save prompt {category}.{name}: {e}")
            raise

    def toggle_module(self, category: str, name: str, enabled: bool):
        """切换模块启用状态"""
        try:
            module = self.config["modules"][category][name]
            if module["required"] and not enabled:
                raise ValueError(f"必需模块 {module['display_name']} 不能禁用")

            module["enabled"] = enabled
            self._save_config()
            logging.info(f"Toggled module {category}.{name}: {enabled}")
        except Exception as e:
            logging.error(f"Failed to toggle module {category}.{name}: {e}")
            raise

    def reset_to_default(self, category: str, name: str):
        """重置为默认提示词"""
        try:
            module = self.config["modules"][category][name]
            file_path = module["file"]

            # 删除自定义文件
            if os.path.exists(file_path):
                os.remove(file_path)

            logging.info(f"Reset prompt to default: {category}.{name}")
        except Exception as e:
            logging.error(f"Failed to reset prompt {category}.{name}: {e}")
            raise

    def _save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Failed to save config: {e}")
            raise

    def _get_prompt_key(self, category: str, name: str) -> str:
        """根据category和name获取prompt_key"""
        # 映射关系
        mapping = {
            ("architecture", "core_seed"): "core_seed_prompt",
            ("architecture", "character_dynamics"): "character_dynamics_prompt",
            # ... 其他映射
        }
        return mapping.get((category, name), "")
```

### 4.2 修改现有模块

#### **4.2.1 修改 `architecture.py`**

```python
# architecture.py (部分代码)
from prompt_manager import PromptManager

def Novel_architecture_generate(...):
    pm = PromptManager()

    # Step1: 核心种子（必需）
    if "core_seed_result" not in partial_data:
        gui_log(f"▶ [1/{total_steps}] 核心种子生成")
        prompt_core = pm.get_prompt("architecture", "core_seed").format(
            topic=topic, genre=genre, ...
        )
        core_seed_result = invoke_with_cleaning(llm_adapter, prompt_core, ...)
        partial_data["core_seed_result"] = core_seed_result

    # Step2: 角色动力学（可选）
    if pm.is_module_enabled("architecture", "character_dynamics"):
        if "character_dynamics_result" not in partial_data:
            gui_log(f"▶ [2/{total_steps}] 角色动力学生成")
            prompt_character = pm.get_prompt("architecture", "character_dynamics").format(...)
            character_dynamics_result = invoke_with_cleaning(...)
            partial_data["character_dynamics_result"] = character_dynamics_result
    else:
        gui_log(f"▷ [2/{total_steps}] 角色动力学 (已禁用，跳过)")
        partial_data["character_dynamics_result"] = "（已跳过角色动力学生成）"

    # Step3: 世界观（可选）
    if pm.is_module_enabled("architecture", "world_building"):
        if "world_building_result" not in partial_data:
            gui_log(f"▶ [3/{total_steps}] 世界观构建")
            prompt_world = pm.get_prompt("architecture", "world_building").format(...)
            world_building_result = invoke_with_cleaning(...)
            partial_data["world_building_result"] = world_building_result
    else:
        gui_log(f"▷ [3/{total_steps}] 世界观 (已禁用，跳过)")
        partial_data["world_building_result"] = "（已跳过世界观构建）"

    # Step4: 三幕式情节（可选）
    if pm.is_module_enabled("architecture", "plot_architecture"):
        if "plot_arch_result" not in partial_data:
            gui_log(f"▶ [4/{total_steps}] 三幕式情节架构")
            prompt_plot = pm.get_prompt("architecture", "plot_architecture").format(...)
            plot_arch_result = invoke_with_cleaning(...)
            partial_data["plot_arch_result"] = plot_arch_result
    else:
        gui_log(f"▷ [4/{total_steps}] 三幕式情节 (已禁用，跳过)")
        partial_data["plot_arch_result"] = "（已跳过三幕式情节架构）"
```

#### **4.2.2 修改 `prompt_definitions.py`**

合并全局System Prompt管理：

```python
# prompt_definitions.py
from prompt_manager import PromptManager

def resolve_global_system_prompt(enabled: bool) -> str:
    """根据开关决定是否加载全局 system prompt"""
    if not enabled:
        return ""

    pm = PromptManager()
    if not pm.is_module_enabled("helper", "global_system"):
        return ""

    prompt = pm.get_prompt("helper", "global_system")
    if not prompt:
        logging.warning("启用全局 system prompt 但未找到有效内容")
        return ""
    return prompt
```

---

## 🎨 五、GUI界面设计

### 5.1 整体布局

**新增页签**：在主TabView中添加"提示词管理"

```
┌────────────────────────────────────────────────────────────────────────┐
│  TabView: 主界面 | 小说架构 | ... | 提示词管理 | 设置                      │
├────────────────────────────────────────────────────────────────────────┤
│  【提示词管理】                                                            │
├──────────────┬───────────────────────────┬───────────────────────────┤
│              │                           │                           │
│  模块列表     │   编辑器区域               │   操作面板                 │
│  (TreeView)  │   (CTkTextbox)            │   (Controls)              │
│              │                           │                           │
│  ▼ 架构生成   │  模块：核心种子生成         │  ☑ 启用此模块             │
│   🔒核心种子 │  ─────────────────────    │                           │
│   ☑ 角色动力 │  [大号文本编辑框]          │  说明：                   │
│   ☑ 世界观   │                           │  生成小说的核心主题、      │
│   ☑ 三幕情节 │  你是专业的小说策划师...   │  类型和冲突               │
│              │  用户提供的主题：{topic}   │                           │
│  ▼ 目录生成   │  小说类型：{genre}         │  🔄 重置为默认            │
│   🔒章节蓝图 │  ...                      │  📥 导入模板              │
│   ☑ 分卷架构 │                           │  📤 导出模板              │
│              │                           │                           │
│  ▼ 章节生成   │                           │  ℹ️ 支持的变量：          │
│   🔒第一章   │                           │  {topic} - 主题          │
│   🔒后续章节 │                           │  {genre} - 类型          │
│   ☑ 章节摘要 │                           │  {num_chapters} - 章数   │
│              │                           │  ...                     │
│  ▼ 定稿阶段   │                           │                           │
│   ☑ 前文摘要 │                           │  字数：1234              │
│   ☑ 角色状态 │                           │                           │
│   ☑ 卷总结   │                           │  💾 保存修改              │
│              │                           │                           │
│  ▼ 辅助功能   │                           │  状态：✅ 已保存          │
│   ☑ 知识搜索 │                           │                           │
│   ☑ 知识过滤 │                           │                           │
│   ☑ 全局提示 │                           │                           │
└──────────────┴───────────────────────────┴───────────────────────────┘
```

### 5.2 组件详细说明

#### **左侧：模块列表（CTkScrollableFrame + TreeView风格）**

- **分组显示**：架构生成、目录生成、章节生成、定稿阶段、辅助功能
- **复选框**：每个模块前显示复选框，控制启用/禁用
- **必需标识**：必需模块显示🔒图标，复选框禁用（不可取消勾选）
- **选中高亮**：点击模块名，加载到编辑器

**实现方式**：
```python
# 使用 CTkScrollableFrame + 自定义布局
for category, modules in pm.config["modules"].items():
    category_label = ctk.CTkLabel(left_frame, text=category_name, font=("", 14, "bold"))
    for name, module in modules.items():
        # 复选框 + 模块名 + 锁图标（如果必需）
        checkbox = ctk.CTkCheckBox(...)
        if module["required"]:
            checkbox.configure(state="disabled")
```

#### **中间：编辑器区域**

- **模块名标题**：显示当前编辑的模块名称和描述
- **大号文本框**：`CTkTextbox`，支持多行编辑
- **变量高亮**：可选功能，高亮显示 `{topic}`、`{genre}` 等变量
- **字数统计**：实时显示字符数

#### **右侧：操作面板**

- **启用开关**：`CTkSwitch`，与左侧复选框联动
- **模块说明**：显示模块的详细描述
- **重置按钮**：重置为默认提示词
- **导入/导出按钮**：导入/导出提示词模板
- **变量说明**：列出当前提示词支持的所有变量
- **保存按钮**：保存修改到文件
- **状态指示**：显示保存状态（已保存/未保存）

---

## 📝 六、实现步骤

### 阶段1：基础架构（核心功能）✅

**目标**：完成配置文件和管理器类

1. ✅ 创建 `prompts_config.json` 配置文件
2. ✅ 创建 `custom_prompts/` 目录
3. ✅ 实现 `PromptManager` 类
4. ✅ 初始化默认提示词文件（从 `prompt_definitions.py` 导出）
5. ✅ 单元测试 `PromptManager`

**预计时间**：2-3小时

### 阶段2：后端集成（逻辑改造）✅

**目标**：让现有生成流程支持可选模块

1. ✅ 修改 `architecture.py` 支持可选模块
2. ✅ 修改 `blueprint.py` 支持可选模块
3. ✅ 修改 `chapter.py` 支持可选模块
4. ✅ 修改 `finalization.py` 支持可选模块
5. ✅ 修改 `prompt_definitions.py` 集成 System Prompt
6. ✅ 测试跳过模块的行为

**预计时间**：3-4小时

### 阶段3：GUI实现（用户界面）✅

**目标**：完整的提示词管理界面

1. ✅ 创建 `ui/prompt_manager_tab.py`
2. ✅ 实现左侧模块列表（TreeView风格）
3. ✅ 实现中间编辑器区域
4. ✅ 实现右侧操作面板
5. ✅ 联动逻辑（复选框、编辑器、保存）
6. ✅ 集成到主窗口

**预计时间**：4-5小时

### 阶段4：高级功能（可选增强）🚀

1. 🚀 导入/导出提示词模板
2. 🚀 预设模板库（简单小说、复杂小说、轻小说等）
3. 🚀 变量高亮和自动完成
4. 🚀 提示词版本管理
5. 🚀 在线预览效果

**预计时间**：根据需求评估

---

## ✅ 七、设计决策总结

| 问题 | 决策 | 理由 |
|------|------|------|
| **禁用模块后的行为** | 跳过该步骤，在架构文件中标记"已跳过" | 保留痕迹，用户清楚哪些被跳过 |
| **必需模块判定** | 核心种子、章节蓝图、第一章/后续章节草稿 | 这些是生成的基础，不可省略 |
| **GUI放置位置** | 独立页签"提示词管理" | 更直观，易于访问和管理 |
| **自定义提示词存储** | 独立txt文件 `custom_prompts/xxx.txt` | 清晰、可读、易于版本管理 |
| **System Prompt管理** | 纳入提示词管理系统 | 统一管理，替代原有的 `global_prompt.json` |

---

## 🔄 八、向下兼容性

### 8.1 现有功能不受影响

- 默认所有模块启用，行为与当前完全一致
- 不使用提示词管理功能，系统按原方式运行
- `prompt_definitions.py` 保留，作为默认值来源

### 8.2 全局 System Prompt 已集成

**全局提示词现已完全集成到提示词管理系统**：

1. 开关控制：`prompts_config.json` → `modules.helper.global_system.enabled`
2. 内容存储：`custom_prompts/system_prompt.txt`
3. UI 管理：提示词管理页签 → 辅助功能 → 全局System Prompt
4. 旧文件 `global_prompt.json` 已不再使用

---

## 📚 九、用户文档

### 9.1 快速入门

**禁用某个模块**：
1. 打开"提示词管理"页签
2. 找到要禁用的模块（如"世界观构建"）
3. 取消勾选复选框
4. 系统自动保存

**自定义提示词**：
1. 在左侧选择要编辑的模块
2. 在中间编辑器修改内容
3. 点击"保存修改"按钮
4. 下次生成将使用自定义版本

**重置为默认**：
1. 选择要重置的模块
2. 点击"重置为默认"按钮
3. 确认操作

### 9.2 常见问题

**Q：禁用"角色动力学"后会怎样？**
A：架构生成阶段会跳过角色设定，直接进入世界观或情节架构。`Novel_architecture.txt` 中会标记"（已跳过角色动力学生成）"。

**Q：必需模块可以禁用吗？**
A：不可以。核心种子、章节蓝图等必需模块是生成的基础，无法禁用。

**Q：修改提示词后会立即生效吗？**
A：是的，保存后下次生成会使用新的提示词。

---

## 🎯 十、成功标准

### 功能完整性
- ✅ 17个提示词模块全部可管理
- ✅ 可选模块支持启用/禁用
- ✅ 支持在线编辑提示词
- ✅ 自定义内容持久化保存
- ✅ System Prompt纳入统一管理

### 用户体验
- ✅ GUI界面直观易用
- ✅ 操作响应及时（保存、加载 < 1秒）
- ✅ 错误提示清晰
- ✅ 支持一键重置

### 性能指标
- ✅ 配置文件加载时间 < 100ms
- ✅ 提示词文件读取 < 50ms
- ✅ GUI响应时间 < 200ms

### 兼容性
- ✅ 默认行为与当前一致
- ✅ 不影响现有功能
- ✅ 平滑迁移 `global_prompt.json`

---

## 📅 十一、时间规划

| 阶段 | 任务 | 预计时间 | 负责人 |
|------|------|---------|--------|
| 阶段1 | 基础架构 | 2-3小时 | Claude |
| 阶段2 | 后端集成 | 3-4小时 | Claude |
| 阶段3 | GUI实现 | 4-5小时 | Claude |
| 测试 | 功能测试 | 1-2小时 | 用户+Claude |
| 总计 | - | **10-14小时** | - |

---

## 📄 十二、附录

### 12.1 变量映射表

各提示词支持的变量列表：

| 提示词 | 支持的变量 |
|--------|-----------|
| `core_seed_prompt` | `{topic}`, `{genre}`, `{number_of_chapters}`, `{word_number}`, `{user_guidance}` |
| `character_dynamics_prompt` | `{core_seed}`, `{user_guidance}` |
| `world_building_prompt` | `{core_seed}`, `{user_guidance}` |
| `plot_architecture_prompt` | `{core_seed}`, `{character_dynamics}`, `{world_building}`, `{user_guidance}` |
| ... | ... |

### 12.2 默认提示词来源

所有默认提示词内容来自 `D:\project\AutoNovel\prompt_definitions.py`，初始化时会自动导出到 `custom_prompts/` 目录。

### 12.3 相关文件清单

**新增文件**：
- `prompts_config.json` - 配置文件
- `prompt_manager.py` - 管理器类
- `ui/prompt_manager_tab.py` - GUI界面
- `custom_prompts/*.txt` - 自定义提示词文件（17个）

**修改文件**：
- `novel_generator/architecture.py` - 支持可选模块
- `novel_generator/blueprint.py` - 支持可选模块
- `novel_generator/chapter.py` - 支持可选模块
- `novel_generator/finalization.py` - 支持可选模块
- `prompt_definitions.py` - 集成System Prompt到PromptManager
- `ui/main_window.py` - 添加提示词管理页签

**已完成的集成**：
- ✅ 全局 System Prompt 已完全集成到 PromptManager
- ✅ 旧文件 `global_prompt.json` 已弃用，改用 `custom_prompts/system_prompt.txt`
- ✅ 所有生成流程统一使用 PromptManager 读取配置

---

## 🚀 开始实施

确认设计方案后，按照以下顺序实施：

1. **阶段1**：创建配置文件和管理器类 → 测试基础功能
2. **阶段2**：修改后端逻辑 → 测试跳过模块
3. **阶段3**：实现GUI界面 → 完整功能测试

每个阶段完成后进行测试，确保功能正确再进入下一阶段。

---

**设计完成日期**：2025-10-01
**实施开始日期**：待定
**预计完成日期**：待定
