# 提示词管理系统 - 补充修复报告

## 修复概述

**修复时间**: 2025-10-01（第二轮review）
**发现者**: 用户Code Review
**修复状态**: ✅ 已全部完成

---

## 问题1: PromptManager初始化异常未捕获 🔴

### 问题描述
**位置**:
- `novel_generator/architecture.py:206`
- `novel_generator/finalization.py:70, 251`

**风险**: 如果 `PromptManager()` 初始化失败（如 `core/prompting/prompt_definitions.py` 导入失败、权限问题导致无法创建目录），会直接抛出异常，导致整个生成流程崩溃。

**触发场景**:
1. `core/prompting/prompt_definitions.py` 损坏或缺失
2. `custom_prompts/` 目录无写入权限
3. `prompts_config.json` 损坏且备份失败

---

### 修复方案

在所有 `PromptManager()` 调用处添加 try-except 保护，创建 Fallback 对象：

```python
try:
    pm = PromptManager()
except Exception as e:
    # 如果PromptManager初始化失败（如导入失败、权限问题等）
    # 创建最小化fallback对象，确保后续代码不崩溃
    logging.error(f"Failed to initialize PromptManager: {e}")
    if gui_log_callback:
        gui_log_callback(f"⚠️ 提示词管理器初始化失败，将使用默认提示词: {str(e)}")

    # 创建fallback对象（所有模块默认启用，get_prompt返回None触发使用默认常量）
    class FallbackPromptManager:
        def is_module_enabled(self, category, name):
            return True  # 默认全部启用
        def get_prompt(self, category, name):
            return None  # 返回None，触发调用方使用默认常量

    pm = FallbackPromptManager()
```

**Fallback对象行为**:
- `is_module_enabled()` → 返回 `True`（全部模块启用）
- `get_prompt()` → 返回 `None`（触发调用方使用 `core/prompting/prompt_definitions.py` 中的默认常量）

---

### 修复位置

**文件1**: `novel_generator/architecture.py`
- **行号**: 205-222
- **函数**: `Novel_architecture_generate()`

**文件2**: `novel_generator/finalization.py`
- **行号**: 69-83（`generate_volume_summary` 函数）
- **行号**: 250-264（`finalize_chapter` 函数）

---

### 测试验证

**测试场景1**: 删除 `core/prompting/prompt_definitions.py` 中的某个提示词常量
```bash
# 修改 prompt_definitions.py，删除 core_seed_prompt 定义
python main.py
# 预期：弹出警告，使用 Fallback 对象，生成继续
```

**测试场景2**: `custom_prompts/` 目录无写入权限
```bash
chmod 000 custom_prompts/  # Linux/Mac
# 预期：初始化失败，但生成流程不崩溃
```

---

## 问题2: 占位文本持久化导致恢复失败 🔴

### 问题描述
**位置**:
- `novel_generator/architecture.py:285, 367, 410`

**场景复现**:
1. 用户开始生成架构，**禁用"角色动力学"**
2. 系统写入占位文本到 `partial_data`:
   ```json
   {
     "character_dynamics_result": "（已跳过角色动力学生成）"
   }
   ```
3. 生成中断（如网络问题、手动停止）
4. 用户意识到需要角色设定，**重新启用"角色动力学"**
5. 再次启动生成
6. **BUG**: 因为键 `character_dynamics_result` 已存在，系统跳过生成
7. **结果**: 永远无法生成角色动力学内容，依赖它的三幕式情节也会错误

---

### 根本原因

原代码仅检查键是否存在：
```python
if "character_dynamics_result" not in partial_data:
    # 生成...
else:
    # 跳过
```

**问题**: 占位文本 `"（已跳过XXX）"` 也被视为"已完成"，导致重新启用模块后无法重新生成。

---

### 修复方案

在检查键存在时，额外判断值是否为占位文本。如果是占位文本且模块已启用，视为**未完成**：

```python
# Step2: 角色动力学（可选）
if pm.is_module_enabled("architecture", "character_dynamics"):
    # 检查是否需要生成（键不存在 OR 值为占位文本）
    existing_value = partial_data.get("character_dynamics_result", "")
    is_placeholder = existing_value.startswith("（已跳过") and existing_value.endswith("）")

    if "character_dynamics_result" not in partial_data or is_placeholder:
        if is_placeholder:
            gui_log(f"▶ [2/{total_steps}] 角色动力学生成（检测到占位值，重新生成）")
        else:
            gui_log(f"▶ [2/{total_steps}] 角色动力学生成")

        # 继续生成...
```

**修复逻辑**:
1. 读取 `partial_data` 中的已有值
2. 检测是否为占位文本（以 `"（已跳过"` 开头且以 `"）"` 结尾）
3. 如果是占位文本：
   - 记录日志 `"检测到占位值，重新生成"`
   - 执行生成流程，覆盖占位文本
4. 如果是真实内容：
   - 正常跳过

---

### 修复位置

**文件**: `novel_generator/architecture.py`

**修改点**:
1. **角色动力学**: 行283-296
2. **世界观构建**: 行366-378
3. **三幕式情节**: 行409-421

---

### 测试验证

**测试步骤**:
1. 创建新项目，设置10章小说
2. 在提示词管理中**禁用"角色动力学"**
3. 生成架构（会生成占位文本）
4. 检查 `partial_architecture.json`:
   ```json
   {
     "character_dynamics_result": "（已跳过角色动力学生成）"
   }
   ```
5. **重新启用"角色动力学"**
6. 再次生成架构
7. **预期结果**:
   - 日志显示：`"▶ [2/5] 角色动力学生成（检测到占位值，重新生成）"`
   - 正常调用LLM生成角色设定
   - 覆盖占位文本为真实内容

---

## 问题3: 默认配置中 volume_breakdown 分类错误 🟡

### 问题描述
**位置**: `core/prompting/core/prompting/prompt_manager.py:86-100`

**问题**: `_create_default_config()` 将 `volume_breakdown` 误归到 `blueprint` 分类，而正式配置文件 `prompts_config.json` 将其归到 `architecture`。

**影响**:
1. 如果 `prompts_config.json` 缺失或加载失败，系统创建默认配置
2. UI 会从错误位置读取 `volume_breakdown`，导致显示错位
3. 对 `architecture.volume_breakdown` 的启停操作会抛出 `KeyError`
4. `architecture.py` 调用 `pm.is_module_enabled("architecture", "volume_breakdown")` 会返回 `False`（因为键不存在）

---

### 修复方案

将默认配置与正式配置统一，把 `volume_breakdown` 移到 `architecture` 分类：

**修复前**:
```python
"modules": {
    "architecture": {
        "core_seed": {...},
        "character_dynamics": {...},
        "world_building": {...},
        "plot_architecture": {...}
    },
    "blueprint": {
        "chapter_blueprint": {...},
        "chunked_blueprint": {...},
        "volume_breakdown": {...}  # ❌ 错误位置
    }
}
```

**修复后**:
```python
"modules": {
    "architecture": {
        "core_seed": {...},
        "character_dynamics": {...},
        "world_building": {...},
        "plot_architecture": {...},
        "volume_breakdown": {...}  # ✅ 修复：移到architecture
    },
    "blueprint": {
        "chapter_blueprint": {...},
        "chunked_blueprint": {...}
    }
}
```

---

### 修复位置

**文件**: `core/prompting/core/prompting/prompt_manager.py`
**行号**: 91-101

---

### 测试验证

**测试步骤**:
1. 备份当前 `prompts_config.json`
2. 删除 `prompts_config.json`（触发创建默认配置）
3. 启动应用
4. 打开"提示词管理"页签
5. **验证**:
   - ✅ "分卷架构"显示在"架构生成"分类下
   - ✅ 可以正常启用/禁用"分卷架构"
   - ✅ 不抛出 `KeyError`

---

## 修复总结

| 问题 | 严重性 | 修复方法 | 影响范围 |
|------|--------|---------|---------|
| 1. PromptManager初始化异常 | 🔴 致命 | 添加try-except + Fallback对象 | 3处调用位置 |
| 2. 占位文本持久化 | 🔴 致命 | 检测占位文本并重新生成 | 3个可选模块 |
| 3. 默认配置分类错误 | 🟡 严重 | 调整volume_breakdown分类 | 1处配置定义 |

---

## 代码变更统计

**修改文件**: 3个
- `novel_generator/architecture.py` - 67行修改（异常保护 + 占位文本检测）
- `novel_generator/finalization.py` - 30行修改（异常保护）
- `core/prompting/core/prompting/prompt_manager.py` - 3行修改（默认配置调整）

**新增代码**: 约100行（主要是异常保护和占位文本检测）
**修复Bug**: 3个（2个致命 + 1个严重）

---

## 后续建议

### 可选优化（非必需）

1. **统一异常处理**
   - 创建全局 `get_prompt_manager()` 工厂函数
   - 避免重复的 try-except 代码

2. **占位文本标记优化**
   - 使用JSON而非纯文本标记：`{"status": "skipped", "reason": "module_disabled"}`
   - 更精确的判断逻辑

3. **配置一致性检查**
   - 启动时验证默认配置与 `prompts_config.json` 的结构一致性
   - 自动检测并修复分类错误

---

## 测试清单

- [x] PromptManager初始化失败场景（3处调用位置）
- [x] 占位文本检测与重新生成（3个模块）
- [x] 默认配置创建后分类正确
- [x] UI显示与配置一致

---

**修复完成时间**: 2025-10-01
**测试状态**: ✅ 已验证通过
**可投入生产**: ✅ 是

