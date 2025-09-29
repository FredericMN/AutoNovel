# 本地 Ollama Embedding 使用指南

本文档说明如何在本项目中使用本地 Ollama 作为向量嵌入（Embedding）服务，以及它如何帮助保持剧情的一致性与连贯性。

## 1. 向量如何帮助保持一致性/连贯性？
- 本项目在章节定稿后，会将章节内容切分并写入本地向量库（Chroma）。参见代码：novel_generator/finalization.py:85。
- 在生成后续章节草稿时，会从向量库按语义相似度检索与当前章节相关的片段，拼接到提示词中，辅助模型保持人物设定、前文细节与剧情线索的连续性。参见：
  - novel_generator/chapter.py:439 调用 `get_relevant_context_from_vector_store(...)`
  - novel_generator/chapter.py:564 传递 `embedding_retrieval_k` 用于控制 Top-K 检索条数
  - novel_generator/vectorstore_utils.py:211 定义具体的相似度检索逻辑
- 向量检索是“事实回忆”的重要补充，结合项目里的 `global_summary.txt` 和 `character_state.txt`（在定稿时更新）共同提升一致性，但并不能百分之百消除所有剧情断裂。

## 2. 安装与启动 Ollama（Windows）
1) 安装：
   - 访问 https://ollama.com 下载 Windows 安装包并安装。
2) 启动服务：
   - 安装后 Ollama 服务通常会自动启动，默认监听 `http://localhost:11434`。
   - 如需手动启动，可在终端运行：
     - `ollama serve`
3) 防火墙与端口：
   - 首次运行可能触发防火墙弹窗，请允许访问。

## 3. 拉取 Embedding 模型
Ollama 需要先拉取支持 Embedding 的模型。例如：
- 推荐通用：
  - `nomic-embed-text`（轻量，速度快）
  - `mxbai-embed-large`（精度更高但更大）
- 拉取命令（任选其一）：
```
ollama pull nomic-embed-text
# 或
ollama pull mxbai-embed-large
```

## 4. 本地接口连通性自检
- 使用 curl 验证：
```
curl http://localhost:11434/api/embeddings -d '{"model":"nomic-embed-text","prompt":"你好，向量！"}'
```
- 返回中应包含 `embedding` 数组（若报错 `model not found`，说明还未 pull 对应模型）。

## 5. 在本项目中配置 Ollama Embedding
方式 A：通过 GUI 配置（推荐）
- 打开 GUI -> Config -> “Embedding settings” 选项卡：
  - `Interface`/`Format` 选择：`Ollama`
  - `Base URL`：`http://localhost:11434`
  - `Model Name`：`nomic-embed-text`（或你已拉取的模型名）
  - `API Key`：留空（Ollama 本地无需密钥）
  - `Retrieval Top-K`：建议 3~6，默认 4
- 点击“保存配置”，再点击“测试 Embedding 配置”，应显示“✅ Embedding配置测试成功！”

方式 B：直接编辑 config.json（进阶）
- 在 `embedding_configs` 中新增/覆盖 `Ollama` 配置，并将 `last_embedding_interface_format` 设为 `Ollama`：
```
{
  "last_embedding_interface_format": "Ollama",
  "embedding_configs": {
    "Ollama": {
      "api_key": "",
      "base_url": "http://localhost:11434",
      "model_name": "nomic-embed-text",
      "retrieval_k": 4,
      "interface_format": "Ollama"
    }
  }
}
```
- 重新打开 GUI 或点击“加载配置”。

## 6. 使用流程建议
1) 先生成“章节草稿”。
2) 点击“定稿章节”：
   - 这一步会更新 `global_summary.txt`、`character_state.txt` 并将章节切分后写入向量库（`<保存目录>/vectorstore`）。
3) 继续生成下一章草稿：
   - 系统将按需从向量库检索相关片段，辅助保持前后呼应。

## 7. 切换嵌入模型时的注意事项
- Chroma 向量库要求维度一致。若你更换了嵌入模型（例如从 `OpenAI` 切到 `Ollama`，或从 `nomic-embed-text` 切到 `mxbai-embed-large`），建议先清空旧的向量库以免维度不匹配导致报错：
  - GUI 中使用“清空向量库”按钮；或手动删除 `<保存目录>/vectorstore` 文件夹。
- 清空后，再从最新章节开始定稿以重建向量库。

## 8. 常见问题排查
- “测试 Embedding 失败 / 连接错误”：
  - 确认 Ollama 服务已启动：`http://localhost:11434` 可访问。
  - 防火墙未拦截；端口未被占用。
- “model not found”：
  - 先执行 `ollama pull <模型名>`。
- “定稿时报错（与 OpenAI API Key 相关）”：
  - 这是切换前的配置遗留。将“Embedding settings”的 `Interface` 改为 `Ollama` 并保存，即可避免云端鉴权。
- “检索不到相关片段或上下文不准”：
  - 提高 `Retrieval Top-K`（如 6）；
  - 调整章节切分策略（当前在 novel_generator/vectorstore_utils.py 中固定 500 字左右的片段，可按需优化）；
  - 继续多写几章并定稿，向量库规模增大后检索效果会提升。

## 9. 代码位置速览（便于二次开发）
- 定稿时向量库写入：novel_generator/finalization.py:85
- 检索与拼接上下文：novel_generator/chapter.py:439, novel_generator/chapter.py:564
- 向量检索实现：novel_generator/vectorstore_utils.py:211
- Ollama 嵌入适配器：embedding_adapters.py 中 `OllamaEmbeddingAdapter`

## 10. 结论
- 使用本地 Ollama 作为嵌入服务可以避免云端 Key 与网络不稳定问题，并实现“可控、可复现”的本地知识检索。
- 向量检索与 `global_summary/character_state` 的双保险有助于保证人物设定、关键线索与剧情连贯性，但最终质量仍受模型生成与提示词设计影响；建议结合“一致性审校”功能一起使用。
