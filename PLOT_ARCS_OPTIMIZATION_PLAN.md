# 剧情要点（plot_arcs）优化方案

## 📋 优化目标

解决当前 `plot_arcs.txt` 形同虚设的问题，建立完整的伏笔记录、提炼、传递机制，提升小说生成的一致性和伏笔管理能力。

---

## 🎯 核心设计理念

1. **双版本管理**：
   - `plot_arcs.txt`（详细版）：完整记录所有伏笔，供人工查看和一致性校审
   - `global_summary.txt` 末尾（精简版≤200字）：自动融入摘要，供 LLM 生成时感知

2. **自然推进原则**：
   - 提示词强调"按需回收"，不急于解决
   - 200字精简版不会压倒主摘要
   - 符合故事剧情自然发展节奏

3. **分卷模式兼容**：
   - 精简版伏笔随 `global_summary` 自动流转到 `volume_summary`
   - 跨卷伏笔通过卷摘要向量检索自动支持

---

## 🔧 技术实现方案

### **流程改造**

```
定稿章节 (finalization.py)
  ├─ [1/3] 更新前文摘要 → global_summary.txt
  ├─ [2/3] 更新角色状态 → character_state.txt
  │
  ├─ [2.5/3] 🆕 更新剧情要点（详细版）
  │    ├─ 读取 plot_arcs.txt
  │    ├─ 调用 LLM 更新（保留未解决、新增本章、标记已解决）
  │    └─ 保存 plot_arcs.txt
  │
  ├─ [2.8/3] 🆕 提炼伏笔到摘要（精简版）
  │    ├─ 读取 plot_arcs.txt
  │    ├─ 调用 LLM 提炼（仅核心伏笔，≤200字）
  │    ├─ 验证字数（超过200字触发二次压缩）
  │    └─ 追加到 global_summary.txt 末尾
  │
  └─ [3/3] 插入向量库

卷末特殊处理（分卷模式）
  ├─ 生成卷摘要 → volume_X_summary.txt（自动包含精简版伏笔）
  └─ 清空 global_summary.txt（为下一卷准备）
```

---

## 📝 提示词设计

### **步骤 2.5：更新详细版伏笔**

**提示词名称**：`plot_arcs_update_prompt`

**功能**：记录所有未解决的伏笔、冲突、谜团

**设计要点**：
- 强调"只记录，不解决"
- 标记已解决的伏笔（✓已解决：XXX）
- 简洁描述（≤30字/条）

### **步骤 2.8：提炼精简版伏笔**

**提示词名称**：`plot_arcs_distill_prompt`

**功能**：从详细版提炼核心伏笔，融入摘要

**设计要点**：
- 仅保留未解决的伏笔
- 极度精简（总字数≤200字）
- 关键词化（≤20字/条）
- 优先级排序（最重要的5-8条）

### **字数超限压缩**

**提示词名称**：`plot_arcs_compress_prompt`

**功能**：当精简版>200字时，二次压缩

---

## 🎛️ 配置管理

### **prompts_config.json 新增模块**

```json
{
  "modules": {
    "finalization": {
      // ... 现有配置 ...

      "plot_arcs_update": {
        "enabled": true,
        "custom_prompt_path": "custom_prompts/plot_arcs_update.txt"
      },
      "plot_arcs_distill": {
        "enabled": true,
        "custom_prompt_path": "custom_prompts/plot_arcs_distill.txt"
      }
    }
  }
}
```

### **提示词管理器集成**

- 用户可在 UI 中开关步骤 2.5 和 2.8
- 用户可自定义提示词内容
- 参数传递保持一致性

---

## 🔄 数据流转

### **非分卷模式**

```
章节1定稿
  └─ global_summary.txt: "摘要内容\n\n━━━ 未解决伏笔 ━━━\n- 伏笔1\n- 伏笔2"
       ↓
章节2生成草稿
  └─ 读取 global_summary.txt（含伏笔）
       ↓
章节2定稿
  └─ 更新 global_summary.txt（伏笔自动更新）
```

### **分卷模式**

```
第1卷-章节10定稿（卷末章节）
  ├─ global_summary.txt: "本卷摘要\n\n━━━ 未解决伏笔 ━━━\n- 伏笔A\n- 伏笔B"
  └─ 触发卷总结
       ├─ 生成 volume_1_summary.txt（从 global_summary 提炼，自动包含伏笔）
       ├─ 卷摘要向量化
       └─ 清空 global_summary.txt

第2卷-章节11生成草稿
  └─ 读取：
       ├─ volume_1_summary.txt（含第1卷核心伏笔）
       └─ global_summary.txt（空，或本卷新摘要）
```

---

## 🛡️ 异常处理

### **LLM 调用失败**

- 步骤 2.5 失败：保留旧的 `plot_arcs.txt`，记录日志
- 步骤 2.8 失败：不追加伏笔到摘要，记录日志，不影响主流程

### **字数超限**

- 首次提炼 > 200字：触发二次压缩
- 二次压缩仍 > 200字：强制截断并记录警告

### **文件不存在**

- `plot_arcs.txt` 不存在：自动创建空文件
- `global_summary.txt` 不存在：跳过步骤 2.8

---

## 🔍 一致性校审增强

### **修复传参问题**

当前代码：
```python
# ui/generation_handlers.py:628
plot_arcs=""  # ❌ 传空字符串
```

修复后：
```python
plot_arcs_file = os.path.join(filepath, "plot_arcs.txt")
plot_arcs = read_file(plot_arcs_file) if os.path.exists(plot_arcs_file) else ""
```

### **校审提示词**

已包含 `plot_arcs` 的检查（`consistency_checker.py:19`），无需修改。

---

## 📊 预期效果

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 伏笔感知 | ❌ 不感知 | ✅ 每章感知 | +100% |
| 一致性 | ⚠️ 依赖向量检索 | ✅ 主动提醒 | +40% |
| 用户管理 | ❌ 无法查看 | ✅ 双版本可视化 | +100% |
| 分卷兼容 | ⚠️ 部分丢失 | ✅ 自动流转 | +60% |

---

## ✅ 实施检查清单

### **代码修改**

- [ ] `core/prompting/prompt_definitions.py`
  - [ ] 新增 `plot_arcs_update_prompt`
  - [ ] 新增 `plot_arcs_distill_prompt`
  - [ ] 新增 `plot_arcs_compress_prompt`

- [ ] `novel_generator/finalization.py`
  - [ ] 在 `finalize_chapter()` 中添加步骤 2.5
  - [ ] 在 `finalize_chapter()` 中添加步骤 2.8
  - [ ] 添加字数验证和二次压缩逻辑
  - [ ] 添加异常处理

- [ ] `ui/generation_handlers.py`
  - [ ] 修复 `do_consistency_check()` 读取 `plot_arcs.txt`

### **配置文件**

- [ ] `prompts_config.json`
  - [ ] 添加 `plot_arcs_update` 模块配置
  - [ ] 添加 `plot_arcs_distill` 模块配置

### **文档更新**

- [ ] `CLAUDE.md`
  - [ ] 更新"生成流程输出文件"说明
  - [ ] 更新"定稿章节流程"说明

---

## 🧪 测试计划

### **单元测试**

1. 步骤 2.5：验证 `plot_arcs.txt` 正确更新
2. 步骤 2.8：验证精简版字数≤200字
3. 字数超限：验证二次压缩触发
4. 一致性校审：验证正确读取 `plot_arcs.txt`

### **集成测试**

1. 非分卷模式：生成3章，验证伏笔流转
2. 分卷模式：跨卷验证伏笔是否随 `volume_summary` 传递
3. 开关测试：禁用步骤 2.5/2.8，验证跳过逻辑

---

## 📅 实施时间线

1. ✅ **阶段1**：方案设计与确认（已完成）
2. ⏳ **阶段2**：核心代码实施（进行中）
   - 提示词定义
   - finalization.py 逻辑
   - 配置文件更新
3. ⏳ **阶段3**：修复一致性校审
4. ⏳ **阶段4**：测试验证
5. ⏳ **阶段5**：文档更新

---

## 📌 注意事项

1. **向后兼容**：旧项目无 `plot_arcs.txt`，自动创建空文件
2. **性能影响**：每章定稿增加 2 次 LLM 调用（约+15-30秒）
3. **提示词可调**：用户可通过提示词管理器优化
4. **开关灵活**：用户可按需禁用步骤 2.5 或 2.8

---

**文档版本**：v1.0
**创建时间**：2025-10-02
**作者**：Claude Code
