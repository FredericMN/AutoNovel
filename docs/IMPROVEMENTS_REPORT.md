# 提示词管理系统改进报告

## 改进背景

基于用户提出的潜在风险分析，实施了两项高优先级改进措施，提升系统的健壮性和用户体验。

## 改进1：模块依赖关系管理 ✅

### 问题分析
**原问题**: 禁用 `character_dynamics` 后，依赖它的 `plot_architecture` 模块会使用 "（已跳过角色动力学生成）" 作为变量值，导致生成的内容不完整。

**影响范围**:
- `plot_architecture` 依赖 `character_dynamics` 和 `world_building`
- `create_character_state` 依赖 `character_dynamics`

### 解决方案

#### 1.1 配置文件增强
在 `prompts_config.json` 中为每个模块添加 `dependencies` 字段：

```json
{
  "plot_architecture": {
    "enabled": true,
    "required": false,
    "display_name": "三幕式情节",
    "dependencies": ["character_dynamics", "world_building"],
    "variables": [...]
  }
}
```

**依赖关系图**:
```
character_dynamics
    ├─→ plot_architecture (间接依赖)
    └─→ create_character_state (直接依赖)

world_building
    └─→ plot_architecture (间接依赖)
```

#### 1.2 依赖检查机制
在 `PromptManager.toggle_module()` 中实现依赖检查：

```python
def toggle_module(self, category: str, name: str, enabled: bool):
    # 禁用模块时，检查是否有其他启用的模块依赖它
    if not enabled:
        dependent_modules = self._find_dependent_modules(category, name)
        if dependent_modules:
            raise ValueError(
                f"无法禁用 {module_name}\n\n"
                f"以下模块依赖它：\n• 三幕式情节\n• 初始角色状态\n\n"
                f"请先禁用这些模块，或保持启用状态。"
            )
```

**用户体验**:
- ✅ 尝试禁用被依赖的模块时，弹出明确的错误提示
- ✅ 列出所有依赖该模块的模块名称
- ✅ 提供明确的操作建议（先禁用依赖模块）

#### 1.3 实现效果

**测试场景**: 尝试禁用 `character_dynamics`

**预期行为**:
1. 系统检测到 `plot_architecture` 和 `create_character_state` 依赖它
2. 弹出错误对话框：
   ```
   无法禁用 角色动力学

   以下模块依赖它：
   • 三幕式情节
   • 初始角色状态

   请先禁用这些模块，或保持启用状态。
   ```
3. 操作被拒绝，复选框恢复选中状态

**正确禁用流程**:
1. 先禁用 `plot_architecture`
2. 再禁用 `create_character_state`
3. 最后禁用 `character_dynamics` ✅

---

## 改进2：配置文件验证与备份 ✅

### 问题分析
**原问题**: `prompts_config.json` 格式错误时，系统直接创建默认配置，可能导致用户自定义设置丢失。

**风险场景**:
1. 用户手动编辑JSON时出现语法错误
2. 文件损坏或编码问题
3. 版本更新导致格式不兼容

### 解决方案

#### 2.1 配置验证机制
在 `load_config()` 中添加格式验证：

```python
def _validate_config(self, config: dict) -> bool:
    """验证配置文件格式"""
    # 检查必需字段
    if "modules" not in config:
        return False

    # 检查每个模块的必需字段
    for category, modules in config["modules"].items():
        for name, module_data in modules.items():
            required_fields = ["enabled", "required"]
            for field in required_fields:
                if field not in module_data:
                    logging.error(f"Module {category}.{name} missing '{field}'")
                    return False

    return True
```

**验证检查项**:
- ✅ `modules` 字段存在性
- ✅ 每个模块包含 `enabled` 字段
- ✅ 每个模块包含 `required` 字段
- ✅ JSON 格式正确性（`json.JSONDecodeError`捕获）

#### 2.2 自动备份机制
配置验证失败时，自动备份原文件：

```python
def _backup_config(self):
    """备份配置文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{self.config_path}.backup_{timestamp}"
    shutil.copy2(self.config_path, backup_path)
    print(f"⚠️ 配置文件格式错误，已备份至: {backup_path}")
```

**备份文件命名**: `prompts_config.json.backup_20251001_143052`

**备份时机**:
1. JSON 解析错误（语法错误）
2. 格式验证失败（缺少必需字段）
3. 其他加载异常

#### 2.3 降级策略
备份后自动创建默认配置，确保系统可用：

```python
try:
    config = json.load(f)
    if self._validate_config(config):
        return config  # 正常返回
    else:
        self._backup_config()  # 验证失败→备份
        return self._create_default_config()  # 使用默认
except json.JSONDecodeError:
    self._backup_config()  # 解析失败→备份
    return self._create_default_config()  # 使用默认
```

#### 2.4 用户体验

**场景1**: JSON 语法错误
```
[ERROR] JSON parse error in prompts_config.json: line 15, column 8
⚠️ 配置文件格式错误，已备份至: prompts_config.json.backup_20251001_143052
[INFO] Using default configuration
```

**场景2**: 缺少必需字段
```
[ERROR] Module architecture.core_seed missing field 'enabled'
⚠️ 配置文件格式错误，已备份至: prompts_config.json.backup_20251001_143052
[INFO] Config validation failed, creating backup and using default
```

**用户恢复步骤**:
1. 查看备份文件找回自定义设置
2. 修复JSON错误
3. 重启应用验证配置

---

## 技术实现细节

### 文件修改清单

#### 1. `prompts_config.json`
- ✅ 添加 `dependencies` 字段到所有17个模块
- ✅ 更新说明文档（`_note` 字段）

#### 2. `core/prompting/core/prompting/prompt_manager.py`
**新增方法**:
- `_validate_config(config)` - 配置验证
- `_backup_config()` - 自动备份
- `_find_dependent_modules(category, name)` - 查找依赖模块

**修改方法**:
- `load_config()` - 添加验证和备份逻辑
- `toggle_module()` - 添加依赖检查逻辑
- `_get_prompt_key()` - 修正 `volume_breakdown` 路径

#### 3. `novel_generator/architecture.py`
- ✅ 修正 `volume_breakdown` 模块路径从 `blueprint` 到 `architecture`

#### 4. 辅助脚本
- `scripts/maintenance/add_dependencies.py` - 批量添加 dependencies 字段

### 依赖关系完整列表

| 被依赖模块 | 依赖它的模块 | 依赖类型 |
|-----------|------------|---------|
| character_dynamics | plot_architecture | 变量依赖 |
| character_dynamics | create_character_state | 必需依赖 |
| world_building | plot_architecture | 变量依赖 |

**其他模块**: 无依赖关系（`dependencies: []`）

### 错误处理流程

```
用户点击复选框禁用模块
    ↓
PromptManager.toggle_module()
    ↓
检查 required=true？
    ├─ 是 → 抛出错误："必需模块不能禁用"
    └─ 否 → 继续
    ↓
检查是否有启用的模块依赖它？
    ├─ 是 → 抛出错误："以下模块依赖它：..."
    └─ 否 → 继续
    ↓
更新 enabled 状态
    ↓
保存配置文件
    ↓
更新 GUI 显示
```

---

## 测试验证

### 测试用例1：依赖检查
**步骤**:
1. 启动应用，打开"提示词管理"页签
2. 取消勾选"角色动力学"

**预期结果**:
- ❌ 操作被拒绝
- 📋 弹出错误提示，列出依赖模块
- ✅ 复选框恢复选中状态

**实际结果**: ✅ 通过

### 测试用例2：配置备份
**步骤**:
1. 手动修改 `prompts_config.json`，删除一个模块的 `enabled` 字段
2. 重启应用

**预期结果**:
- 📁 生成备份文件 `prompts_config.json.backup_YYYYMMDD_HHMMSS`
- ⚠️ 控制台输出备份路径
- 🔄 使用默认配置启动

**实际结果**: ✅ 通过

### 测试用例3：正常禁用流程
**步骤**:
1. 先禁用"三幕式情节"
2. 再禁用"初始角色状态"
3. 最后禁用"角色动力学"

**预期结果**:
- ✅ 所有操作成功
- 💾 配置正确保存

**实际结果**: ✅ 通过

---

## 用户指南

### 如何禁用有依赖的模块

**场景**: 想要禁用"角色动力学"

**正确步骤**:
1. 进入"提示词管理"页签
2. 先禁用依赖它的模块：
   - 取消勾选"三幕式情节"
   - 取消勾选"初始角色状态"（在"辅助功能"分类）
3. 再取消勾选"角色动力学"

**提示**: 如果不确定依赖关系，直接尝试禁用，系统会提示哪些模块依赖它。

### 配置文件损坏后如何恢复

**步骤**:
1. 查找备份文件：`prompts_config.json.backup_YYYYMMDD_HHMMSS`
2. 对比备份文件和当前配置，找出错误
3. 修复错误后保存
4. 重启应用验证

**常见错误**:
- 缺少逗号或多余逗号
- 引号不匹配
- 中文标点符号（应使用英文标点）

---

## 技术亮点

1. **主动防御**: 依赖检查在操作发生前拦截，避免生成无效配置
2. **用户友好**: 错误提示清晰明确，提供具体的操作建议
3. **数据安全**: 自动备份机制防止配置丢失
4. **降级保护**: 验证失败时自动使用默认配置，保证系统可用
5. **可追溯**: 备份文件带时间戳，方便追溯历史配置

---

## 后续优化建议

### 已完成 ✅
- [x] 模块依赖关系管理
- [x] 依赖检查和警告
- [x] 配置文件验证
- [x] 自动备份机制

### 未来可选改进 📋
- [ ] JSON Schema 验证（更严格的格式检查）
- [ ] 配置文件可视化编辑器
- [ ] 依赖关系可视化图表
- [ ] 批量启用/禁用模块功能
- [ ] 配置模板导入/导出
- [ ] 版本迁移工具（跨版本配置升级）

---

## 总结

本次改进成功解决了用户提出的两个高优先级风险：

1. **依赖关系管理**: 通过依赖检查机制，防止因禁用被依赖模块导致的生成错误
2. **配置安全保护**: 通过验证和备份机制，防止配置错误导致的数据丢失

系统的健壮性和用户体验得到显著提升，为后续功能扩展奠定了坚实基础。

---

**完成时间**: 2025-10-01
**状态**: ✅ 全部完成，可投入生产
**负责人**: Claude Code

