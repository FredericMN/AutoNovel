# PromptManager 安全使用指南

本文档说明如何使用 `core/prompting/prompt_manager_helper.py` 提供的辅助函数，确保提示词加载的健壮性。

## 核心原则

1. **永远不要直接调用 `.format()` 在未检查的 PromptManager 返回值上**
2. **使用辅助函数自动处理 None/空串/异常情况**
3. **保留默认提示词常量作为 fallback**

---

## 方法一: 使用便捷函数（推荐）

最简洁的方式，自动处理所有异常和 fallback：

```python
from core.prompting.prompt_manager_helper import get_blueprint_prompt
from core.prompting.prompt_definitions import chapter_blueprint_prompt

# 自动初始化 PromptManager 并获取提示词（失败时使用 fallback）
prompt_template = get_blueprint_prompt(
    "chapter_blueprint",
    chapter_blueprint_prompt
)

# 安全使用，不会抛出 AttributeError
prompt = prompt_template.format(
    novel_architecture=architecture_text,
    number_of_chapters=number_of_chapters
)
```

**优点**:
- 一行代码搞定，最简洁
- 自动处理所有边界情况
- 自动记录警告日志

---

## 方法二: 共享 PromptManager 实例

适用于同一函数内多次获取提示词的场景：

```python
from core.prompting.prompt_manager_helper import get_prompt_manager, get_blueprint_prompt
from core.prompting.prompt_definitions import chapter_blueprint_prompt, chunked_chapter_blueprint_prompt

# 函数入口处初始化一次
pm = get_prompt_manager()  # 永不抛异常，失败返回 Fallback 对象

# 多次使用
prompt1 = get_blueprint_prompt("chapter_blueprint", chapter_blueprint_prompt, pm=pm)
prompt2 = get_blueprint_prompt("chunked_blueprint", chunked_chapter_blueprint_prompt, pm=pm)
```

**优点**:
- 避免重复初始化 PromptManager
- 性能更好（函数内多次调用时）

---

## 方法三: 通用函数（最灵活）

适用于需要自定义行为的场景：

```python
from core.prompting.prompt_manager_helper import get_prompt_manager, get_prompt_with_fallback
from core.prompting.prompt_definitions import first_chapter_draft_prompt

pm = get_prompt_manager()

prompt_template = get_prompt_with_fallback(
    category="chapter",
    name="first_chapter",
    fallback_prompt=first_chapter_draft_prompt,
    pm=pm,
    warn_on_fallback=True  # 可选：控制是否记录警告
)

prompt = prompt_template.format(...)
```

**优点**:
- 完全控制参数
- 可以跨模块使用（不限于特定类型）

---

## 实际案例

### 案例1: blueprint.py 中的分块生成

**修改前（❌ 不安全）**:
```python
pm = PromptManager()  # 可能抛异常
chunked_prompt = pm.get_prompt("blueprint", "chunked_blueprint")  # 可能返回 None
chunk_prompt = chunked_prompt.format(...)  # ❌ AttributeError!
```

**修改后（✅ 安全）**:
```python
from core.prompting.prompt_manager_helper import get_prompt_manager, get_blueprint_prompt
from core.prompting.prompt_definitions import chunked_chapter_blueprint_prompt

pm = get_prompt_manager()  # 永不抛异常

chunked_prompt = get_blueprint_prompt(
    "chunked_blueprint",
    chunked_chapter_blueprint_prompt,
    pm=pm
)
chunk_prompt = chunked_prompt.format(...)  # ✅ 安全，一定有值
```

---

### 案例2: chapter.py 中的摘要生成

**修改前（❌ 不安全）**:
```python
pm = PromptManager()
summary_prompt = pm.get_prompt("chapter", "chapter_summary")
prompt = summary_prompt.format(...)  # ❌ 可能崩溃
```

**修改后（✅ 安全）**:
```python
from core.prompting.prompt_manager_helper import get_chapter_prompt
from core.prompting.prompt_definitions import summarize_recent_chapters_prompt

# 一行搞定，自动处理所有异常
summary_prompt = get_chapter_prompt(
    "chapter_summary",
    summarize_recent_chapters_prompt
)
prompt = summary_prompt.format(...)  # ✅ 绝对安全
```

---

## 迁移检查清单

将现有代码迁移到安全模式时，检查以下模式：

### ❌ 危险模式（需要修复）

```python
# 模式1: 直接初始化无保护
pm = PromptManager()

# 模式2: 直接获取无检查
prompt = pm.get_prompt("category", "name")
result = prompt.format(...)  # ❌ 可能崩溃

# 模式3: 虽有检查但不完整
prompt = pm.get_prompt("category", "name")
if prompt:  # ⚠️ 空字符串也会通过
    result = prompt.format(...)
```

### ✅ 安全模式

```python
# 推荐方式：使用辅助函数
from core.prompting.prompt_manager_helper import get_chapter_prompt
from core.prompting.prompt_definitions import next_chapter_draft_prompt

prompt = get_chapter_prompt("next_chapter", next_chapter_draft_prompt)
result = prompt.format(...)  # ✅ 绝对安全
```

---

## FAQ

**Q: 使用辅助函数后，用户自定义提示词还能生效吗？**
A: 能。辅助函数优先使用 PromptManager 加载的自定义提示词，只有失败时才 fallback。

**Q: 性能会受影响吗？**
A: 几乎无影响。PromptManager 初始化只在函数入口执行一次，后续都是读取操作。

**Q: 需要修改所有旧代码吗？**
A: 建议修改，但不强制。旧代码可以继续用原有的 `try/except + if not prompt` 模式。

**Q: 辅助函数能否用在 GUI 代码中？**
A: 可以，但 GUI 代码通常直接调用 `novel_generator` 模块，无需直接操作 PromptManager。

---

## 总结

| 方法 | 适用场景 | 代码量 | 安全性 |
|------|---------|--------|--------|
| 便捷函数 | 单次调用 | 最少 | ✅ 最高 |
| 共享实例 | 多次调用 | 中等 | ✅ 最高 |
| 通用函数 | 自定义需求 | 较多 | ✅ 最高 |
| 原始方式 | 不推荐 | 最多 | ❌ 低 |

**建议**: 新代码一律使用便捷函数，旧代码逐步迁移。



