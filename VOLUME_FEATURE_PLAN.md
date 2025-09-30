# 分卷功能实现方案

## 📋 项目概述

为 AutoNovel 长篇小说生成工具添加分卷功能，解决超过30章的长篇小说在剧情连贯性、prompt长度控制和伏笔管理方面的问题。

---

## 一、当前流程分析

### 现有四步流程：
1. **架构生成** (architecture.py): 核心种子 → 角色动力学 → 世界观 → 三幕式情节
2. **蓝图生成** (blueprint.py): 分块生成所有章节目录
3. **章节草稿** (chapter.py): 基于前3章+向量检索生成
4. **定稿章节** (finalization.py): 更新全局摘要、角色状态、向量库

### 现有问题（长篇小说）：
- global_summary.txt 越来越长
- 向量检索范围过大，噪音增多
- 缺乏阶段性的剧情收束

---

## 二、分卷模式核心设计

### 2.1 数据结构变化

**配置文件新增字段 (config.json)**
```json
{
  "other_params": {
    "num_volumes": 3,  // 分卷数量（0/1=不分卷，>1=分卷）
    "num_chapters": 70,
    // ...现有字段
  }
}
```

**新增文件结构**
```
filepath/
├── Novel_architecture.txt          # 总架构
├── Volume_architecture.txt         # 分卷架构（新增）
├── Novel_directory.txt             # 章节目录
├── volume_1_summary.txt            # 第一卷总结（新增）
├── volume_2_summary.txt            # 第二卷总结（新增）
├── global_summary.txt              # 全局摘要（不分卷模式）
├── character_state.txt
└── chapters/
```

### 2.2 章节分配逻辑

**原则：**
- 总章节数必须是5的倍数
- 每卷章节数尽量是5的倍数
- 章节编号全局累计

**示例：** 70章分3卷
```
第一卷: 第1-20章   (20章)
第二卷: 第21-40章  (20章)
第三卷: 第41-70章  (30章)
```

**算法：**
```python
def calculate_volume_ranges(num_chapters, num_volumes):
    base = (num_chapters // num_volumes // 5) * 5  # 向下取整到5的倍数
    ranges = []
    start = 1
    for i in range(num_volumes):
        if i < num_volumes - 1:
            end = start + base - 1
        else:
            end = num_chapters  # 最后一卷包含剩余所有章节
        ranges.append((start, end))
        start = end + 1
    return ranges
```

---

## 三、生成流程重构

### 3.1 Step 1: 架构生成 (architecture.py)

**现有步骤不变：**
1. 核心种子
2. 角色动力学
3. 世界观
4. 三幕式情节（总体）

**新增步骤5（仅分卷模式）：分卷规划**

**新增 Prompt (prompt_definitions.py)**
```python
volume_breakdown_prompt = """
基于以下小说架构：
{novel_architecture}

需要将故事分为 {num_volumes} 卷，总共 {num_chapters} 章。

请为每一卷设计三幕式结构，要求：
1. 每卷形成相对完整的叙事单元（有起承转合）
2. 卷与卷之间通过伏笔和角色成长连接
3. 最后一卷收束全部主线

输出格式：

第一卷（第{vol1_start}-{vol1_end}章）
卷标题：[为本卷起一个副标题]
核心冲突：[本卷的主要矛盾]
├── 第一幕（触发）：[起因事件]
├── 第二幕（对抗）：[矛盾升级]
├── 第三幕（解决）：[阶段性结局]
└── 卷末伏笔：[为下一卷铺垫的3个关键要素]

第二卷（第{vol2_start}-{vol2_end}章）
卷标题：[副标题]
核心冲突：[升级的矛盾]
├── 承接点：[如何继承第一卷]
├── 第一幕（触发）：[新触发]
├── 第二幕（对抗）：[深层冲突]
├── 第三幕（解决）：[阶段性结局]
└── 卷末伏笔：[铺垫要素]

...（以此类推）

仅返回最终文本，不要解释。
"""
```

**实现函数**
```python
def generate_volume_architecture(
    llm_adapter,
    novel_architecture: str,
    num_volumes: int,
    num_chapters: int,
    volume_ranges: list,  # [(1,20), (21,40), (41,70)]
    system_prompt: str,
    gui_log_callback=None
) -> str:
    """生成分卷架构"""
    # 构建 prompt 参数
    format_params = {
        "novel_architecture": novel_architecture,
        "num_volumes": num_volumes,
        "num_chapters": num_chapters,
    }
    # 动态添加每卷的范围
    for i, (start, end) in enumerate(volume_ranges, 1):
        format_params[f"vol{i}_start"] = start
        format_params[f"vol{i}_end"] = end

    prompt = volume_breakdown_prompt.format(**format_params)
    result = invoke_with_cleaning(llm_adapter, prompt, system_prompt)
    return result
```

**修改 Novel_architecture_generate()**
```python
# 在 Step4 完成后添加
if num_volumes > 1:
    gui_log("▶ [6/6] 分卷架构规划")
    volume_ranges = calculate_volume_ranges(number_of_chapters, num_volumes)
    volume_arch_result = generate_volume_architecture(
        llm_adapter,
        final_content,  # 传入总架构
        num_volumes,
        number_of_chapters,
        volume_ranges,
        system_prompt,
        gui_log_callback
    )
    # 保存到 Volume_architecture.txt
    volume_arch_file = os.path.join(filepath, "Volume_architecture.txt")
    save_string_to_txt(volume_arch_result, volume_arch_file)
    gui_log("   └─ ✅ 分卷架构完成")
```

---

### 3.2 Step 2: 蓝图生成 (blueprint.py)

**调整策略：**
- **不分卷模式**：保持现有逻辑
- **分卷模式**：按卷生成，每卷传入该卷的情节规划

**新增 Prompt**
```python
volume_chapter_blueprint_prompt = """
基于以下元素：
- 小说架构：{novel_architecture}
- 分卷架构：{volume_architecture}

当前任务：生成第 {current_volume} 卷的章节蓝图

本卷信息：
- 章节范围：第{volume_start}-{volume_end}章
- 本卷情节：
{current_volume_plot}

前面卷的总结（如果有）：
{previous_volumes_summary}

请生成第{volume_start}-{volume_end}章的详细蓝图，格式与要求：
（...后续与 chapter_blueprint_prompt 相同）
"""
```

**修改 Chapter_blueprint_generate()**
```python
def Chapter_blueprint_generate(
    # ...现有参数
    num_volumes: int = 1,  # 新增
    # ...
):
    if num_volumes <= 1:
        # 原有逻辑不变
        pass
    else:
        # 分卷生成逻辑
        volume_arch_file = os.path.join(filepath, "Volume_architecture.txt")
        volume_architecture = read_file(volume_arch_file)
        volume_ranges = calculate_volume_ranges(number_of_chapters, num_volumes)

        for vol_num, (vol_start, vol_end) in enumerate(volume_ranges, 1):
            gui_log(f"\n▶ 生成第{vol_num}卷蓝图（第{vol_start}-{vol_end}章）")

            # 提取当前卷的情节
            current_volume_plot = extract_volume_plot(volume_architecture, vol_num)

            # 读取前面卷的总结
            previous_summary = ""
            for i in range(1, vol_num):
                summary_file = os.path.join(filepath, f"volume_{i}_summary.txt")
                if os.path.exists(summary_file):
                    previous_summary += f"\n第{i}卷总结：\n{read_file(summary_file)}\n"

            # 生成本卷蓝图
            prompt = volume_chapter_blueprint_prompt.format(
                novel_architecture=architecture_text,
                volume_architecture=volume_architecture,
                current_volume=vol_num,
                volume_start=vol_start,
                volume_end=vol_end,
                current_volume_plot=current_volume_plot,
                previous_volumes_summary=previous_summary
            )
            result = invoke_with_cleaning(llm_adapter, prompt, system_prompt)

            # 追加到 Novel_directory.txt
            # ...
```

---

### 3.3 Step 3: 章节草稿 (chapter.py)

**核心调整：剧情注入逻辑**

**不分卷模式：**
```
前文来源：
- 前3章原文（详细）
- global_summary.txt（全局摘要）
```

**分卷模式：**
```
前文来源：
- 前面卷的总结（简要）volume_X_summary.txt
- 当前卷的前3章（详细）
- 当前卷的 global_summary（详细）
```

**新增工具函数**
```python
def get_volume_context(
    novel_number: int,
    volume_ranges: list,
    filepath: str,
    chapters_dir: str
) -> dict:
    """
    获取分卷模式下的上下文
    返回：{
        "current_volume": 2,
        "previous_volumes_summary": "第一卷总结...",
        "current_volume_chapters": ["ch1_text", "ch2_text", ...]
    }
    """
    current_vol = get_volume_number(novel_number, volume_ranges)
    vol_start, vol_end = volume_ranges[current_vol - 1]

    # 读取前面卷的总结
    prev_summary = ""
    for i in range(1, current_vol):
        summary_file = os.path.join(filepath, f"volume_{i}_summary.txt")
        if os.path.exists(summary_file):
            prev_summary += f"第{i}卷：{read_file(summary_file)}\n\n"

    # 读取当前卷的前N章
    current_vol_chapters = []
    start_chap = max(vol_start, novel_number - 3)
    for c in range(start_chap, novel_number):
        chap_file = os.path.join(chapters_dir, f"chapter_{c}.txt")
        if os.path.exists(chap_file):
            current_vol_chapters.append(read_file(chap_file))

    return {
        "current_volume": current_vol,
        "volume_start": vol_start,
        "volume_end": vol_end,
        "previous_volumes_summary": prev_summary,
        "current_volume_chapters": current_vol_chapters
    }
```

**修改 build_chapter_prompt()**
```python
def build_chapter_prompt(
    # ...现有参数
    num_volumes: int = 1,  # 新增
    # ...
):
    if num_volumes > 1:
        volume_ranges = calculate_volume_ranges(num_chapters, num_volumes)
        volume_ctx = get_volume_context(novel_number, volume_ranges, filepath, chapters_dir)

        # 使用 volume_ctx["previous_volumes_summary"] 替代或补充 global_summary
        # 使用 volume_ctx["current_volume_chapters"] 替代 get_last_n_chapters_text
    else:
        # 原有逻辑
        pass
```

**调整 next_chapter_draft_prompt**
```python
# 在"参考文档"部分添加分卷信息
next_chapter_draft_prompt = """
参考文档：
{%- if num_volumes > 1 %}
└── 分卷信息：
    当前卷：第 {current_volume} 卷（第{volume_start}-{volume_end}章）
    前面卷总结：
    {previous_volumes_summary}
{%- endif %}

└── 前文摘要（当前卷）：
    {global_summary}

└── 前章结尾段：
    {previous_chapter_excerpt}

...（后续不变）
"""
```

---

### 3.4 Step 4: 定稿章节 (finalization.py)

**新增逻辑：检测是否是卷末章节**

**新增函数**
```python
def finalize_volume(
    volume_number: int,
    volume_range: tuple,  # (start, end)
    filepath: str,
    llm_adapter,
    system_prompt: str,
    gui_log_callback=None
):
    """
    总结整卷内容
    """
    gui_log(f"\n▶ 生成第{volume_number}卷总结...")

    vol_start, vol_end = volume_range
    chapters_dir = os.path.join(filepath, "chapters")

    # 读取本卷所有章节
    volume_chapters = []
    for c in range(vol_start, vol_end + 1):
        chap_file = os.path.join(chapters_dir, f"chapter_{c}.txt")
        if os.path.exists(chap_file):
            volume_chapters.append(read_file(chap_file))

    combined_text = "\n\n".join(volume_chapters)

    # 调用 LLM 生成总结
    prompt = volume_summary_prompt.format(
        volume_number=volume_number,
        volume_chapters_text=combined_text[-8000:]  # 截断避免过长
    )

    summary = invoke_with_cleaning(llm_adapter, prompt, system_prompt)

    # 保存
    summary_file = os.path.join(filepath, f"volume_{volume_number}_summary.txt")
    save_string_to_txt(summary, summary_file)

    gui_log(f"   └─ ✅ 第{volume_number}卷总结完成")
```

**新增 Prompt**
```python
volume_summary_prompt = """
以下是第 {volume_number} 卷的所有章节内容：
{volume_chapters_text}

请生成一个简洁的卷总结（500-1000字），包含：
1. 核心剧情发展（主线推进）
2. 主要角色变化（成长轨迹）
3. 关键伏笔和悬念（未解之谜）
4. 为下一卷的铺垫（转场点）

要求：
- 聚焦核心，删除细节
- 客观描述，不展开联想
- 保留关键伏笔和角色关系变化

仅返回总结文本，不要解释。
"""
```

**修改 finalize_chapter()**
```python
def finalize_chapter(
    # ...现有参数
    num_volumes: int = 1,  # 新增
    num_chapters: int = 0,  # 新增
    # ...
):
    # ...原有定稿逻辑

    # 检测是否是卷末章节
    if num_volumes > 1:
        volume_ranges = calculate_volume_ranges(num_chapters, num_volumes)
        if is_volume_last_chapter(novel_number, volume_ranges):
            volume_num = get_volume_number(novel_number, volume_ranges)
            volume_range = volume_ranges[volume_num - 1]
            finalize_volume(
                volume_num,
                volume_range,
                filepath,
                llm_adapter,
                system_prompt,
                gui_log_callback
            )
```

---

## 四、Prompt 不大改原则

**实现策略：**
1. **原有 prompt 保持不变**（用于不分卷模式）
2. **新增分卷专用 prompt**（仅在分卷模式下使用）
3. **通过条件判断切换**

**示例：**
```python
if num_volumes > 1:
    prompt = volume_chapter_blueprint_prompt.format(...)
else:
    prompt = chapter_blueprint_prompt.format(...)
```

---

## 五、UI 调整

**在 novel_params_tab.py 或 main_tab.py 添加：**

```python
# 章节数量输入框（现有）
self.num_chapters_entry = ctk.CTkEntry(...)

# 新增：分卷数量输入框
self.num_volumes_label = ctk.CTkLabel(frame, text="分卷数量（0/1=不分卷）:")
self.num_volumes_entry = ctk.CTkEntry(frame, placeholder_text="0")

# 绑定验证事件
self.num_chapters_entry.bind("<FocusOut>", self.validate_volume_config)
self.num_volumes_entry.bind("<FocusOut>", self.validate_volume_config)

def validate_volume_config(self, event=None):
    """验证分卷配置"""
    try:
        num_chapters = int(self.num_chapters_entry.get() or 0)
        num_volumes = int(self.num_volumes_entry.get() or 0)

        # 验证1：总章节数必须是5的倍数
        if num_chapters % 5 != 0:
            messagebox.showwarning("配置错误", "总章节数必须是5的倍数！")
            return False

        # 验证2：如果分卷，检查每卷章节数
        if num_volumes > 1:
            volume_ranges = calculate_volume_ranges(num_chapters, num_volumes)
            info = "分卷预览：\n"
            for i, (start, end) in enumerate(volume_ranges, 1):
                chapter_count = end - start + 1
                info += f"第{i}卷: 第{start}-{end}章 ({chapter_count}章)\n"
            self.log(info)

        return True
    except ValueError:
        return False
```

---

## 六、新增工具模块 (volume_utils.py)

```python
# volume_utils.py
# -*- coding: utf-8 -*-
"""
分卷相关的工具函数
"""

def calculate_volume_ranges(num_chapters: int, num_volumes: int) -> list:
    """
    计算每卷的章节范围

    Args:
        num_chapters: 总章节数（必须是5的倍数）
        num_volumes: 分卷数量

    Returns:
        [(start, end), ...] 例如 [(1, 20), (21, 40), (41, 70)]
    """
    if num_volumes <= 1:
        return [(1, num_chapters)]

    base = (num_chapters // num_volumes // 5) * 5
    ranges = []
    start = 1

    for i in range(num_volumes):
        if i < num_volumes - 1:
            end = start + base - 1
        else:
            end = num_chapters
        ranges.append((start, end))
        start = end + 1

    return ranges


def get_volume_number(chapter_num: int, volume_ranges: list) -> int:
    """获取章节所属的卷号"""
    for vol_num, (start, end) in enumerate(volume_ranges, 1):
        if start <= chapter_num <= end:
            return vol_num
    return 1


def is_volume_last_chapter(chapter_num: int, volume_ranges: list) -> bool:
    """判断是否是某卷的最后一章"""
    for start, end in volume_ranges:
        if chapter_num == end:
            return True
    return False


def extract_volume_plot(volume_architecture: str, volume_num: int) -> str:
    """
    从 Volume_architecture.txt 中提取指定卷的情节
    """
    import re
    pattern = rf"第{volume_num}卷.*?(?=第{volume_num+1}卷|$)"
    match = re.search(pattern, volume_architecture, re.DOTALL)
    return match.group(0) if match else ""
```

---

## 七、实现优先级（推荐顺序）

### Phase 1: 基础设施 ✅
1. **config.json 添加 num_volumes**
2. **创建 volume_utils.py**
3. **UI 添加分卷输入和验证**

### Phase 2: 架构层 ✅
4. **新增 volume_breakdown_prompt**
5. **修改 architecture.py 添加步骤5**

### Phase 3: 蓝图层 ✅
6. **新增 volume_chapter_blueprint_prompt**
7. **修改 blueprint.py 支持分卷生成**

### Phase 4: 章节层 ✅
8. **新增 volume_summary_prompt**
9. **修改 chapter.py 的 get_volume_context**
10. **修改 finalization.py 添加 finalize_volume**

### Phase 5: 测试优化 ✅
11. **端到端测试（70章分3卷）**
12. **优化向量检索策略**
13. **完善日志输出**

---

## 八、关键优化点

### 8.1 向量检索策略

**分卷后的优先级：**
```python
# 伪代码
if num_volumes > 1:
    # 1. 当前卷的历史章节（高权重）
    current_vol_docs = retrieve_from_volume(current_volume, query, k=4)

    # 2. 前面卷的总结文档（中权重）
    prev_vol_summaries = [read_file(f"volume_{i}_summary.txt") for i in range(1, current_volume)]

    # 3. 外部知识库（保持不变）
    external_docs = retrieve_from_knowledge(query, k=2)

    final_context = combine(current_vol_docs, prev_vol_summaries, external_docs)
```

### 8.2 Prompt 长度控制

**分卷模式的优势：**
- 前面卷只传总结（500-1000字），不传全文
- 当前卷只传前3章+摘要
- 大幅减少 token 消耗

**对比：**
```
不分卷（70章）：
  前文摘要: 10000+ 字
  前3章: 9000 字
  Total: 19000+ 字

分卷（70章分3卷）：
  前2卷总结: 2000 字
  当前卷前3章: 9000 字
  Total: 11000 字（节省40%）
```

---

## 九、示例流程（70章分3卷）

```
用户输入：
- 总章节数: 70
- 分卷数量: 3
- 系统自动计算: 第一卷20章，第二卷20章，第三卷30章

Step 1: 生成架构
  1.1 核心种子
  1.2 角色动力学
  1.3 世界观
  1.4 三幕式情节（总体）
  1.5 分卷规划 ← 新增
      输出: Volume_architecture.txt

Step 2: 生成目录
  2.1 生成第一卷蓝图（第1-20章）
      输入: Volume_architecture(第一卷部分)
      输出: 追加到 Novel_directory.txt
  2.2 生成第二卷蓝图（第21-40章）
      输入: Volume_architecture(第二卷部分) + volume_1_summary.txt
      输出: 追加到 Novel_directory.txt
  2.3 生成第三卷蓝图（第41-70章）
      输入: Volume_architecture(第三卷部分) + volume_1&2_summary.txt
      输出: 追加到 Novel_directory.txt

Step 3: 生成章节
  生成第1章...
  生成第20章...
  → 定稿第20章时，自动生成 volume_1_summary.txt ← 新增

  生成第21章...
    前文来源: volume_1_summary + 第21卷前3章
  生成第40章...
  → 定稿第40章时，自动生成 volume_2_summary.txt ← 新增

  生成第41章...
    前文来源: volume_1&2_summary + 第41卷前3章
  生成第70章...
  → 定稿第70章时，自动生成 volume_3_summary.txt ← 新增
```

---

## 🎯 总结

**实现方案的核心原则：**

1. ✅ **兼容性**：不分卷模式完全保持原有逻辑
2. ✅ **渐进性**：分卷功能通过条件判断逐步注入
3. ✅ **Prompt最小改动**：新增专用 prompt，不修改现有
4. ✅ **三幕式贯穿**：总架构三幕式 → 每卷三幕式 → 章节蓝图
5. ✅ **Token优化**：前面卷只传总结，大幅减少上下文长度