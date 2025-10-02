# AutoNovel 防呆设计优化方案

## 📋 概述

本方案针对用户提出的三个防呆场景进行详细设计，确保系统在非正常操作下能够提前发现问题并给出明确提示。

---

## 🎯 场景一：章节连续性校验

### 问题描述
- **场景1.1**: 没有生成任何章节时，设置章节号不为1
- **场景1.2**: 第3章还没生成，但章节号选择第5章

### 风险分析
- 可能导致章节缺失，破坏小说连续性
- 向量库检索可能找不到前置章节上下文
- 全局摘要和角色状态更新异常

### 优化方案

#### 方案A：智能检测 + 提示（推荐）

**实现位置**: `ui/generation_handlers.py` - `generate_chapter_draft_ui()`

**校验逻辑**:
```python
def validate_chapter_continuity(filepath: str, chapter_num: int) -> dict:
    """
    校验章节连续性

    Returns:
        {
            "valid": bool,           # 是否通过校验
            "error_type": str,       # 错误类型
            "message": str,          # 错误提示
            "suggestion": str,       # 建议操作
            "missing_chapters": list # 缺失的章节号列表
        }
    """
    chapters_dir = os.path.join(filepath, "chapters")

    # 检查是否存在章节目录
    if not os.path.exists(chapters_dir):
        if chapter_num != 1:
            return {
                "valid": False,
                "error_type": "no_chapters_exist",
                "message": f"⚠️ 章节连续性检查失败",
                "suggestion": f"当前没有任何章节，但您设置的章节号为 {chapter_num}。\n建议先生成第1章。",
                "missing_chapters": list(range(1, chapter_num))
            }
        return {"valid": True}

    # 检查已生成的章节
    existing_chapters = []
    for i in range(1, chapter_num):
        chapter_file = os.path.join(chapters_dir, f"chapter_{i}.txt")
        if os.path.exists(chapter_file):
            existing_chapters.append(i)

    # 查找缺失章节
    missing_chapters = []
    for i in range(1, chapter_num):
        if i not in existing_chapters:
            missing_chapters.append(i)

    if missing_chapters:
        return {
            "valid": False,
            "error_type": "missing_chapters",
            "message": f"⚠️ 检测到章节缺失",
            "suggestion": f"要生成第 {chapter_num} 章，需要先完成以下章节：\n{', '.join(map(str, missing_chapters[:5]))}{'...' if len(missing_chapters) > 5 else ''}",
            "missing_chapters": missing_chapters
        }

    return {"valid": True}
```

**用户体验**:
```
╔════════════════════════════════════════════╗
║  ⚠️  章节连续性检查失败                     ║
╠════════════════════════════════════════════╣
║  当前要生成：第 5 章                        ║
║  已生成章节：1, 2                           ║
║  缺失章节：3, 4                             ║
╠════════════════════════════════════════════╣
║  建议操作：                                 ║
║  1. 先生成第 3 章                           ║
║  2. 或者修改章节号为 3                      ║
╠════════════════════════════════════════════╣
║  [ 强制生成 ]  [ 返回修改 ]                ║
╚════════════════════════════════════════════╝
```

**实现细节**:
1. 在生成章节前调用校验函数
2. 如果校验失败，弹出对话框提示
3. 提供两个选项：
   - **强制生成**：允许跳章节生成（用于特殊场景）
   - **返回修改**：关闭对话框，返回修改章节号

#### 方案B：自动修正章节号（可选）

在小说参数区域增加"智能章节号"功能：

```python
def auto_detect_next_chapter(filepath: str) -> int:
    """自动检测下一个应该生成的章节号"""
    chapters_dir = os.path.join(filepath, "chapters")
    if not os.path.exists(chapters_dir):
        return 1

    # 找到最大的连续章节号
    chapter_num = 1
    while True:
        chapter_file = os.path.join(chapters_dir, f"chapter_{chapter_num}.txt")
        if not os.path.exists(chapter_file):
            break
        chapter_num += 1

    return chapter_num
```

**UI增强**: 在章节号输入框旁边添加"🔄 自动检测"按钮

---

## 🎯 场景二：配置一致性校验

### 问题描述
生成架构和目录后，修改了章节数或分卷数

### 风险分析详解

#### 2.1 章节数变化的影响

**场景**: 原本设置30章，生成架构和目录后改为20章

**影响范围**:

| 受影响模块 | 具体影响 | 严重程度 |
|-----------|---------|---------|
| `Novel_directory.txt` | 目录中有30章的标题和大纲，但只会生成20章 | ⚠️ 中等 |
| 向量库元数据 | `chapter_metadata` 字段记录的总章节数不一致 | ⚠️ 中等 |
| 全局摘要生成 | 可能引用不存在的章节信息 | ⚠️ 中等 |
| 分卷逻辑 | 分卷边界计算错误 | 🔴 严重 |

**示例问题**:
```python
# 原配置: 30章, 3卷 → 每卷10章
# 新配置: 20章, 3卷 → 每卷6.67章（计算错误）

# volume_utils.calculate_volume_ranges(20, 3)
# 返回: [(1, 7), (8, 14), (15, 20)]  # 分配不均

# 但 Novel_directory.txt 中仍然标记:
# 第1-10章为第1卷
# 第11-20章为第2卷
# 第21-30章为第3卷（不存在）
```

#### 2.2 分卷数变化的影响

**场景**: 原本设置3卷，生成架构和目录后改为2卷

**影响范围**:

| 受影响模块 | 具体影响 | 严重程度 |
|-----------|---------|---------|
| `Volume_architecture.txt` | 文件中有3卷的架构，但系统只识别2卷 | 🔴 严重 |
| 分卷蓝图 | `Novel_directory.txt` 中章节的卷号标记错误 | 🔴 严重 |
| 向量检索 | `volume_number` 元数据不匹配，检索失败 | 🔴 严重 |
| 卷摘要生成 | `volume_X_summary.txt` 文件混乱 | 🔴 严重 |

**示例问题**:
```python
# 原配置: 30章, 3卷
# Volume_architecture.txt 包含:
# - 第1卷 (1-10章)
# - 第2卷 (11-20章)
# - 第3卷 (21-30章)

# 新配置: 30章, 2卷
# 系统计算: 每卷15章
# - 第1卷 (1-15章)  ← 与原架构不符
# - 第2卷 (16-30章) ← 与原架构不符

# 章节生成时:
# - 第11章以为自己属于第2卷（新逻辑）
# - 但 Volume_architecture.txt 标记为第2卷（旧逻辑）
# - extract_volume_architecture(11) → 提取第2卷架构 ❌
```

### 优化方案

#### 方案A：配置锁定机制（推荐）

**实现位置**: `ui/novel_params_tab.py` + `ui/main_window.py`

**核心逻辑**:

```python
def check_critical_files_exist(filepath: str) -> dict:
    """
    检查关键文件是否存在

    Returns:
        {
            "architecture_exists": bool,
            "directory_exists": bool,
            "volume_architecture_exists": bool,
            "any_chapter_exists": bool,
            "is_locked": bool  # 是否应锁定配置
        }
    """
    result = {
        "architecture_exists": os.path.exists(os.path.join(filepath, "Novel_architecture.txt")),
        "directory_exists": os.path.exists(os.path.join(filepath, "Novel_directory.txt")),
        "volume_architecture_exists": os.path.exists(os.path.join(filepath, "Volume_architecture.txt")),
        "any_chapter_exists": False
    }

    # 检查是否有任何章节生成
    chapters_dir = os.path.join(filepath, "chapters")
    if os.path.exists(chapters_dir):
        for f in os.listdir(chapters_dir):
            if f.startswith("chapter_") and f.endswith(".txt"):
                result["any_chapter_exists"] = True
                break

    # 判断是否应锁定
    result["is_locked"] = result["directory_exists"] or result["any_chapter_exists"]

    return result
```

**UI增强**:

1. **配置项颜色变化**:
   - 未锁定：正常颜色（白底黑字）
   - 已锁定：禁用颜色（灰底灰字）

2. **锁定图标**:
   ```
   章节数: [  30  ] 🔒  ← 已锁定
   分卷数: [  3   ] 🔒  ← 已锁定
   ```

3. **悬停提示**:
   ```
   鼠标悬停在锁定字段上时显示：

   🔒 此参数已锁定

   原因：已生成章节目录

   如需修改，请：
   1. 重新生成架构和目录
   2. 或删除现有目录文件
   ```

4. **强制修改按钮**（管理员模式）:

```python
# 在小说参数区域底部添加
unlock_config_btn = ctk.CTkButton(
    self.params_frame,
    text="🔓 解锁配置（高级）",
    command=self.unlock_critical_config,
    font=("Microsoft YaHei", 10),
    fg_color="#FF6347",  # 红色警告
    height=24
)
```

**解锁对话框**:
```
╔════════════════════════════════════════════╗
║  ⚠️  警告：修改关键配置                     ║
╠════════════════════════════════════════════╣
║  修改章节数或分卷数可能导致：               ║
║                                            ║
║  ❌ 章节目录与实际不符                      ║
║  ❌ 分卷架构错乱                            ║
║  ❌ 向量库元数据不一致                      ║
║  ❌ 已生成章节无法正确引用                  ║
╠════════════════════════════════════════════╣
║  建议操作：                                 ║
║  1. 删除 Novel_directory.txt               ║
║  2. 删除 Volume_architecture.txt           ║
║  3. 重新生成架构和目录                      ║
╠════════════════════════════════════════════╣
║  确定要解锁吗？                             ║
║  [ 我明白风险，继续 ]  [ 取消 ]            ║
╚════════════════════════════════════════════╝
```

#### 方案B：配置变更检测（辅助）

在保存配置时增加变更检测：

```python
def validate_config_changes(old_config: dict, new_config: dict, filepath: str) -> dict:
    """
    检测关键配置变更

    Returns:
        {
            "has_critical_changes": bool,
            "changes": list,  # 变更项列表
            "warnings": list  # 警告信息
        }
    """
    result = {
        "has_critical_changes": False,
        "changes": [],
        "warnings": []
    }

    # 检查章节数变更
    old_chapters = old_config.get("other_params", {}).get("num_chapters", 0)
    new_chapters = new_config.get("other_params", {}).get("num_chapters", 0)

    if old_chapters != new_chapters:
        result["has_critical_changes"] = True
        result["changes"].append(f"章节数: {old_chapters} → {new_chapters}")

        # 检查是否已有目录
        if os.path.exists(os.path.join(filepath, "Novel_directory.txt")):
            result["warnings"].append(
                "已存在章节目录文件，修改章节数可能导致目录与实际不符。\n"
                "建议删除 Novel_directory.txt 并重新生成。"
            )

    # 检查分卷数变更
    old_volumes = old_config.get("other_params", {}).get("num_volumes", 0)
    new_volumes = new_config.get("other_params", {}).get("num_volumes", 0)

    if old_volumes != new_volumes:
        result["has_critical_changes"] = True
        result["changes"].append(f"分卷数: {old_volumes} → {new_volumes}")

        # 检查是否已有分卷架构
        if os.path.exists(os.path.join(filepath, "Volume_architecture.txt")):
            result["warnings"].append(
                "已存在分卷架构文件，修改分卷数会导致卷号计算错误。\n"
                "建议删除 Volume_architecture.txt 并重新生成。"
            )

    return result
```

**保存确认对话框**:
```
╔════════════════════════════════════════════╗
║  ⚠️  检测到关键配置变更                     ║
╠════════════════════════════════════════════╣
║  变更内容：                                 ║
║  • 章节数: 30 → 20                         ║
║  • 分卷数: 3 → 2                           ║
╠════════════════════════════════════════════╣
║  ⚠️  警告：                                 ║
║  • 已存在章节目录文件，修改可能导致不一致   ║
║  • 已存在分卷架构文件，需要重新生成         ║
╠════════════════════════════════════════════╣
║  [ 继续保存 ]  [ 取消 ]                    ║
╚════════════════════════════════════════════╝
```

---

## 🎯 场景三：保存状态可视化提示

### 问题描述
编辑完小说参数后不点保存，但配置实际未生效

### 优化方案

#### 方案A：实时保存状态指示器（推荐）

**实现位置**: `ui/novel_params_tab.py`

**UI布局**:

```
┌─────────────────────────────────────────┐
│ 小说参数                    🟢 已保存   │  ← 状态指示器
├─────────────────────────────────────────┤
│ 主题(Topic):                             │
│ [___________________________________]   │
│                                         │
│ 类型(Genre):                            │
│ [___________________________________]   │
│                                         │
│ ...                                     │
│                                         │
│ [ 💾 保存小说参数 ]                     │
└─────────────────────────────────────────┘
```

**状态指示器设计**:

| 状态 | 颜色 | 图标 | 文字 | 说明 |
|-----|------|------|------|------|
| 已保存 | 🟢 绿色 | ✓ | 已保存 | 当前参数已保存到 config.json |
| 未保存 | 🔴 红色 | ⚠ | 尚未保存 | 有参数修改但未点击保存 |
| 保存中 | 🟡 黄色 | ⟳ | 保存中... | 正在执行保存操作 |

**实现代码**:

```python
class SaveStatusIndicator:
    """保存状态指示器"""

    def __init__(self, parent_frame):
        self.frame = ctk.CTkFrame(parent_frame)

        # 状态图标
        self.status_icon = ctk.CTkLabel(
            self.frame,
            text="🟢",
            font=("Microsoft YaHei", 16)
        )
        self.status_icon.grid(row=0, column=0, padx=3)

        # 状态文字
        self.status_text = ctk.CTkLabel(
            self.frame,
            text="已保存",
            font=("Microsoft YaHei", 11),
            text_color="#00AA00"  # 绿色
        )
        self.status_text.grid(row=0, column=1, padx=3)

        # 最后保存时间
        self.time_label = ctk.CTkLabel(
            self.frame,
            text="",
            font=("Microsoft YaHei", 9),
            text_color="gray"
        )
        self.time_label.grid(row=0, column=2, padx=5)

    def set_saved(self):
        """设置为已保存状态"""
        self.status_icon.configure(text="🟢")
        self.status_text.configure(
            text="已保存",
            text_color="#00AA00"
        )
        from datetime import datetime
        self.time_label.configure(
            text=f"保存于 {datetime.now().strftime('%H:%M:%S')}"
        )

    def set_unsaved(self):
        """设置为未保存状态"""
        self.status_icon.configure(text="🔴")
        self.status_text.configure(
            text="尚未保存",
            text_color="#FF0000"
        )
        self.time_label.configure(text="有未保存的修改")

    def set_saving(self):
        """设置为保存中状态"""
        self.status_icon.configure(text="🟡")
        self.status_text.configure(
            text="保存中...",
            text_color="#FFA500"
        )
        self.time_label.configure(text="")
```

**变更监听**:

```python
def setup_change_listeners(self):
    """为所有输入组件添加变更监听器"""

    # 文本框监听（Topic, User Guidance等）
    def on_text_change(event=None):
        self.save_status_indicator.set_unsaved()

    self.topic_text.bind("<<Modified>>", on_text_change)
    self.user_guide_text.bind("<<Modified>>", on_text_change)
    # ... 其他文本框

    # Entry监听（Genre, Word Number等）
    def on_entry_change(*args):
        self.save_status_indicator.set_unsaved()

    self.genre_var.trace_add("write", on_entry_change)
    self.num_chapters_var.trace_add("write", on_entry_change)
    self.num_volumes_var.trace_add("write", on_entry_change)
    self.word_number_var.trace_add("write", on_entry_change)
    # ... 其他变量
```

**保存操作增强**:

```python
def save_other_params(self):
    """保存小说参数（增强版）"""
    try:
        # 设置为保存中状态
        self.save_status_indicator.set_saving()

        # 执行保存逻辑
        other_params = {
            "topic": self.topic_text.get("0.0", "end").strip(),
            "genre": self.genre_var.get().strip(),
            # ... 其他参数
        }

        # 保存到 config.json
        self.loaded_config["other_params"] = other_params
        save_config(self.loaded_config)

        # 设置为已保存状态
        self.save_status_indicator.set_saved()

        messagebox.showinfo("成功", "小说参数已保存！")
        self.safe_log("✅ 小说参数已保存")

    except Exception as e:
        # 保存失败，恢复未保存状态
        self.save_status_indicator.set_unsaved()
        messagebox.showerror("错误", f"保存失败: {str(e)}")
        self.safe_log(f"❌ 保存失败: {str(e)}")
```

#### 方案B：自动保存提醒（可选）

在切换标签页或执行生成操作时，检测未保存状态并提醒：

```python
def check_unsaved_changes_before_action(self, action_name: str) -> bool:
    """
    在执行重要操作前检查未保存的修改

    Returns:
        bool: True 表示可以继续，False 表示用户取消
    """
    if self.has_unsaved_changes:
        response = messagebox.askyesnocancel(
            "未保存的修改",
            f"检测到小说参数有未保存的修改。\n\n"
            f"是否在{action_name}前保存？\n\n"
            f"点击"是"保存并继续\n"
            f"点击"否"不保存并继续\n"
            f"点击"取消"返回修改",
            icon='warning'
        )

        if response is True:  # 是
            self.save_other_params()
            return True
        elif response is False:  # 否
            return True
        else:  # 取消
            return False

    return True
```

**调用示例**:
```python
def generate_chapter_draft_ui(self):
    """生成章节草稿（增强版）"""
    # 检查未保存的修改
    if not self.check_unsaved_changes_before_action("生成章节"):
        return

    # 继续执行生成逻辑
    # ...
```

---

## 📊 实施优先级建议

| 功能 | 优先级 | 开发量 | 影响范围 |
|-----|-------|--------|---------|
| **场景1：章节连续性校验** | 🔴 高 | 中 | 章节生成流程 |
| **场景2：配置锁定机制** | 🔴 高 | 大 | 小说参数界面 |
| **场景2：配置变更检测** | 🟡 中 | 中 | 保存配置流程 |
| **场景3：保存状态指示器** | 🟢 低 | 中 | 小说参数界面 |
| **场景3：自动保存提醒** | 🟢 低 | 小 | 全局操作拦截 |

---

## 🛠️ 实施计划

### 阶段1：核心防呆（必须）

1. ✅ 章节连续性校验（智能检测 + 提示）
2. ✅ 配置锁定机制（章节数/分卷数锁定）

**预计时间**: 4-6小时

### 阶段2：用户体验增强（推荐）

3. ✅ 保存状态指示器
4. ✅ 配置变更检测与警告

**预计时间**: 3-4小时

### 阶段3：高级功能（可选）

5. ⭕ 自动章节号检测
6. ⭕ 未保存修改提醒

**预计时间**: 2-3小时

---

## 📝 需要修改的文件清单

| 文件 | 修改内容 | 难度 |
|-----|---------|------|
| `ui/generation_handlers.py` | 添加章节连续性校验 | ⭐⭐ |
| `ui/novel_params_tab.py` | 添加配置锁定UI、保存状态指示器 | ⭐⭐⭐ |
| `ui/main_window.py` | 集成校验逻辑、修改保存流程 | ⭐⭐ |
| `core/utils/file_utils.py`（新建或扩展） | 通用校验函数库 | ⭐ |

---

## ❓ 请确认以下问题

1. **场景1优先级**: 是否需要"自动检测下一章"功能，还是只校验即可？
2. **场景2解锁方式**: 解锁配置是否需要密码保护？
3. **场景3保存提醒**: 是否希望在每次切换标签页时都提醒未保存？
4. **实施顺序**: 是否按照阶段1→阶段2→阶段3的顺序实施？

---

## 🎨 UI效果预览（文字版）

### 章节连续性校验对话框
```
┌────────────────────────────────────────┐
│ ⚠️  章节连续性检查失败                  │
├────────────────────────────────────────┤
│ 当前要生成：第 5 章                     │
│ 已生成章节：1, 2                        │
│ 缺失章节：3, 4                          │
├────────────────────────────────────────┤
│ 建议操作：                              │
│ 1. 先生成第 3 章                        │
│ 2. 或者修改章节号为 3                   │
├────────────────────────────────────────┤
│ [ 强制生成 ]  [ 返回修改 ]             │
└────────────────────────────────────────┘
```

### 配置锁定状态
```
┌─────────────────────────────────────────┐
│ 小说结构:                               │
│ 章节数: [  30  ] 🔒                     │
│ 分卷数: [  3   ] 🔒                     │
│                                         │
│ 💡 提示：参数已锁定                      │
│    已生成章节目录，修改可能导致不一致    │
│                                         │
│ [ 🔓 解锁配置（高级）]                  │
└─────────────────────────────────────────┘
```

### 保存状态指示器
```
┌─────────────────────────────────────────┐
│ 小说参数         🔴 尚未保存            │
│                  有未保存的修改          │
├─────────────────────────────────────────┤
│ ...                                     │
│                                         │
│ [ 💾 保存小说参数 ]                     │
└─────────────────────────────────────────┘
```

---

**请您确认以上方案是否符合预期，我将根据您的反馈进行代码实施！** 🚀
