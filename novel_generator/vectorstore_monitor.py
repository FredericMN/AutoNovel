# novel_generator/vectorstore_monitor.py
# -*- coding: utf-8 -*-
"""
向量库质量监控模块
记录检索统计、分析文档使用频率、检测低质量片段
"""
import os
import json
import time
import logging
import hashlib
from typing import Dict, List, Optional
from collections import Counter, defaultdict

STATS_FILE_NAME = "vectorstore_stats.json"

def get_stats_file_path(filepath: str) -> str:
    """获取统计文件路径"""
    return os.path.join(filepath, STATS_FILE_NAME)

def load_stats(filepath: str) -> dict:
    """加载统计数据"""
    stats_file = get_stats_file_path(filepath)

    if not os.path.exists(stats_file):
        return {
            "queries": [],
            "doc_usage": {},
            "query_keywords": Counter(),
            "total_retrievals": 0,
            "empty_results_count": 0
        }

    try:
        with open(stats_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 兼容性处理:转换 query_keywords 为 Counter
            if "query_keywords" in data and isinstance(data["query_keywords"], dict):
                data["query_keywords"] = Counter(data["query_keywords"])
            return data
    except Exception as e:
        logging.warning(f"Failed to load vectorstore stats: {e}")
        return {
            "queries": [],
            "doc_usage": {},
            "query_keywords": Counter(),
            "total_retrievals": 0,
            "empty_results_count": 0
        }

def save_stats(filepath: str, stats: dict):
    """保存统计数据"""
    stats_file = get_stats_file_path(filepath)

    try:
        # 转换 Counter 为 dict 以便序列化
        serializable_stats = stats.copy()
        if "query_keywords" in serializable_stats:
            serializable_stats["query_keywords"] = dict(serializable_stats["query_keywords"])

        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(serializable_stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"Failed to save vectorstore stats: {e}")

def log_retrieval(
    filepath: str,
    query: str,
    retrieved_docs: list,
    chapter_number: int = None
):
    """
    记录一次检索操作

    Args:
        filepath: 项目文件路径
        query: 检索查询词
        retrieved_docs: 检索到的文档列表(每个元素为 {"content": str, ...})
        chapter_number: 当前章节号(可选)
    """
    stats = load_stats(filepath)

    # 记录查询
    query_record = {
        "timestamp": time.time(),
        "query": query,
        "results_count": len(retrieved_docs),
        "chapter_number": chapter_number
    }
    stats["queries"].append(query_record)

    # 统计总检索次数
    stats["total_retrievals"] = stats.get("total_retrievals", 0) + 1

    # 统计空结果
    if len(retrieved_docs) == 0:
        stats["empty_results_count"] = stats.get("empty_results_count", 0) + 1

    # 统计文档使用频率
    if "doc_usage" not in stats:
        stats["doc_usage"] = {}

    for doc in retrieved_docs:
        content = doc.get("content", "")
        if not content:
            continue

        # 使用稳定的SHA1哈希作为文档标识（前400字符）
        doc_id = hashlib.sha1(content[:400].encode('utf-8', errors='ignore')).hexdigest()

        if doc_id not in stats["doc_usage"]:
            stats["doc_usage"][doc_id] = {
                "count": 0,
                "first_seen": time.time(),
                "last_used": time.time(),
                "preview": content[:100]
            }

        stats["doc_usage"][doc_id]["count"] += 1
        stats["doc_usage"][doc_id]["last_used"] = time.time()

    # 统计关键词频率
    if "query_keywords" not in stats:
        stats["query_keywords"] = Counter()

    # 提取查询中的关键词
    keywords = [kw.strip() for kw in query.split() if len(kw.strip()) > 1]
    stats["query_keywords"].update(keywords)

    # 限制查询记录数量(最多保留最近1000条)
    if len(stats["queries"]) > 1000:
        stats["queries"] = stats["queries"][-1000:]

    save_stats(filepath, stats)
    logging.info(f"Logged retrieval: query='{query[:50]}...', results={len(retrieved_docs)}")

def analyze_quality(filepath: str) -> dict:
    """
    分析向量库质量

    Returns:
        dict: 包含质量分析结果的字典
    """
    stats = load_stats(filepath)

    if not stats["queries"]:
        return {
            "status": "no_data",
            "message": "尚无检索记录"
        }

    total_retrievals = stats.get("total_retrievals", len(stats["queries"]))
    empty_count = stats.get("empty_results_count", 0)

    # 1. 计算平均检索结果数
    avg_results = sum(q["results_count"] for q in stats["queries"]) / len(stats["queries"]) if stats["queries"] else 0

    # 2. 检测未使用的文档(从未被检索过的文档需要在向量库遍历时统计)
    # 这里只能统计已被使用的文档

    # 3. 检测过度使用的文档
    doc_usage = stats.get("doc_usage", {})
    if doc_usage:
        usage_counts = [info["count"] for info in doc_usage.values()]
        max_usage = max(usage_counts) if usage_counts else 0
        avg_usage = sum(usage_counts) / len(usage_counts) if usage_counts else 0

        overused_docs = [
            {"doc_id": doc_id, "count": info["count"], "preview": info["preview"]}
            for doc_id, info in doc_usage.items()
            if info["count"] > avg_usage * 3  # 使用次数超过平均值3倍
        ]
        overused_docs.sort(key=lambda x: x["count"], reverse=True)
    else:
        max_usage = 0
        avg_usage = 0
        overused_docs = []

    # 4. 分析查询关键词分布
    query_keywords = stats.get("query_keywords", Counter())
    top_keywords = query_keywords.most_common(10) if query_keywords else []

    # 5. 计算检索效率
    empty_rate = (empty_count / total_retrievals * 100) if total_retrievals > 0 else 0

    analysis = {
        "status": "success",
        "total_retrievals": total_retrievals,
        "empty_results_count": empty_count,
        "empty_rate": f"{empty_rate:.2f}%",
        "avg_results_per_query": f"{avg_results:.2f}",
        "unique_docs_used": len(doc_usage),
        "max_doc_usage": max_usage,
        "avg_doc_usage": f"{avg_usage:.2f}",
        "overused_docs_count": len(overused_docs),
        "overused_docs": overused_docs[:5],  # 只返回前5个
        "top_keywords": top_keywords,
        "recommendations": []
    }

    # 生成建议
    if empty_rate > 30:
        analysis["recommendations"].append("空结果率较高(>30%),建议检查关键词生成逻辑或增加向量库内容")

    if len(overused_docs) > 10:
        analysis["recommendations"].append(f"发现{len(overused_docs)}个高频文档,可能需要拆分或丰富向量库内容")

    if avg_results < 2:
        analysis["recommendations"].append("平均检索结果数较少(<2),建议增加每组关键词的检索数量(k值)")

    if len(doc_usage) < 10:
        analysis["recommendations"].append("被检索到的文档数量较少,向量库内容可能不足或关键词不匹配")

    return analysis

def get_usage_report(filepath: str, top_n: int = 20) -> str:
    """
    生成人类可读的使用报告

    Args:
        filepath: 项目文件路径
        top_n: 返回前N个最常用文档

    Returns:
        str: 格式化的报告文本
    """
    analysis = analyze_quality(filepath)

    if analysis["status"] == "no_data":
        return analysis["message"]

    report = []
    report.append("=" * 60)
    report.append("向量库质量报告")
    report.append("=" * 60)
    report.append(f"总检索次数: {analysis['total_retrievals']}")
    report.append(f"空结果次数: {analysis['empty_results_count']} ({analysis['empty_rate']})")
    report.append(f"平均每次检索结果数: {analysis['avg_results_per_query']}")
    report.append(f"被使用的唯一文档数: {analysis['unique_docs_used']}")
    report.append(f"最高文档使用次数: {analysis['max_doc_usage']}")
    report.append(f"平均文档使用次数: {analysis['avg_doc_usage']}")
    report.append("")

    if analysis["overused_docs"]:
        report.append("-" * 60)
        report.append(f"高频文档 (前{len(analysis['overused_docs'])}个):")
        report.append("-" * 60)
        for i, doc in enumerate(analysis["overused_docs"], 1):
            report.append(f"{i}. 使用{doc['count']}次")
            report.append(f"   预览: {doc['preview']}...")
            report.append("")

    if analysis["top_keywords"]:
        report.append("-" * 60)
        report.append("热门关键词 (前10个):")
        report.append("-" * 60)
        for keyword, count in analysis["top_keywords"]:
            report.append(f"  {keyword}: {count}次")
        report.append("")

    if analysis["recommendations"]:
        report.append("-" * 60)
        report.append("优化建议:")
        report.append("-" * 60)
        for i, rec in enumerate(analysis["recommendations"], 1):
            report.append(f"{i}. {rec}")
        report.append("")

    report.append("=" * 60)

    return "\n".join(report)

def clear_stats(filepath: str):
    """清空统计数据"""
    stats_file = get_stats_file_path(filepath)
    if os.path.exists(stats_file):
        try:
            os.remove(stats_file)
            logging.info("Vectorstore stats cleared")
        except Exception as e:
            logging.warning(f"Failed to clear stats: {e}")
