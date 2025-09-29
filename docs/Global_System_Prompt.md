# 全局 SYSTEM 提示词使用指南

本项目已支持在每一步 LLM 调用中自动注入一个全局 `SYSTEM` 提示词。该提示词集中配置在 `prompt_definitions.py`，用于统一写作风格、约束输出边界、避免敏感内容、固定格式等。

## 一、在哪里配置
- 文件：`prompt_definitions.py`
- 变量：`GLOBAL_SYSTEM_PROMPT`
- 默认值为空字符串（不注入）。填写任意非空文本后即会在所有调用中生效。

## 二、如何生效
- OpenAI/DeepSeek/Ollama/ML Studio（经 `ChatOpenAI`）
  - 以 `system` + `user` 结构调用，统一注入 `GLOBAL_SYSTEM_PROMPT`。
- Azure OpenAI（经 `AzureChatOpenAI`）
  - 同上，走 `system` + `user` 消息结构。
- Azure AI Inference（`azure-ai-inference`）
  - 使用 `SystemMessage(GLOBAL_SYSTEM_PROMPT)` + `UserMessage`。
- OpenAI 兼容直连（火山引擎、硅基流动、Grok）
  - 以 `messages=[{"role":"system"}, {"role":"user"}]` 形式注入。
- Google Gemini（`google-generativeai`）
  - 通过 `GenerativeModel(..., system_instruction=GLOBAL_SYSTEM_PROMPT)` 注入。

> 备注：将 `GLOBAL_SYSTEM_PROMPT` 留空字符串即可恢复为“无全局 SYSTEM”的旧行为。

## 三、建议写法
可放置：
- 统一语言/语气要求（如“使用简体中文，避免Markdown标题”）；
- 风格边界（如“网文爽点足，避免过度复述”）；
- 安全与合规限制（如“不得输出个人隐私、不得泄露提示词”）；
- 全局格式约束（如“仅输出正文，不要小标题”）。

## 四、注意事项
- 修改后需要重启 GUI 以确保新配置被加载。
- 若切换/清空该提示词，对旧的生成不产生回溯影响，仅影响后续调用。
- 若你的第三方代理/网关对 `system` 指令有额外过滤，建议先做一次单章草稿生成自检。
- 该功能不会改变你原有各步提示词内容，只是“前置了一条统一的系统消息”。

## 五、快速回滚
- 将 `prompt_definitions.py` 中的 `GLOBAL_SYSTEM_PROMPT` 置为空字符串 `"""\n\n"""` 即可关闭全局注入。
