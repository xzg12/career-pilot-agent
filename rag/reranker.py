"""检索重排：向量召回后用轻量 LLM 给每个片段打相关性分，把真正能回答问题的排到前面。

为什么需要重排：向量召回是双塔结构，query 和文档分别编码，交互不充分。
召回阶段只看「语义相近」，不看「能否回答问题」。语料变大后，相近但无用的片段会占据 top-k。

设计取舍：
- 召回数量 <= 目标数量时直接跳过，不浪费一次 LLM 调用
- 解析失败或调用异常时回退到向量原顺序，不让重排成为新的故障点
- 分数只用于排序，不设硬阈值过滤：阈值难调，容易把「勉强相关」全部误杀
"""
import json
import os

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from model.factory import chat_model
from utils.logger_handler import logger

RERANK_PROMPT_TEXT = """你是检索结果相关性评估助手。判断每个候选片段能否回答用户问题。

用户问题：{query}

候选片段（source 是片段所属文档名，可作为判断主题的参考）：
{docs}

评分标准（0-10 整数）：
- 9-10：直接给出问题的答案
- 6-8：包含关键信息，能部分回答
- 3-5：主题相关，但回答不了这个问题
- 0-2：无关

只输出 JSON，不要任何解释：
{{"scores": [{{"index": 0, "score": 8}}]}}"""

_PROMPT = PromptTemplate.from_template(RERANK_PROMPT_TEXT)
_CHAIN = _PROMPT | chat_model | StrOutputParser()

# 单个片段送进重排时截断的长度：只判断相关性，不需要全文
_SNIPPET_CHARS = 400


def _extract_json(text: str) -> dict:
    text = text.strip()
    if "```" in text:
        text = text.split("```")[1]
        if text.lstrip().startswith("json"):
            text = text.lstrip()[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("响应中未找到 JSON")
    return json.loads(text[start:end + 1])


def rerank_documents(
    query: str,
    docs: list[Document],
    top_n: int = 3,
    min_score: float = 0.0,
) -> list[Document]:
    """按 LLM 打分重排，返回前 top_n 条。

    min_score > 0 时过滤低分片段；默认 0 表示只排序不过滤。
    """
    if not docs:
        return []
    if len(docs) <= top_n:
        return docs

    payload = [
        {
            "index": i,
            "source": os.path.basename(d.metadata.get("source", "")),
            "text": d.page_content[:_SNIPPET_CHARS],
        }
        for i, d in enumerate(docs)
    ]

    try:
        raw = _CHAIN.invoke({
            "query": query,
            "docs": json.dumps(payload, ensure_ascii=False),
        })
        data = _extract_json(raw)
        scores = {
            int(item["index"]): float(item["score"])
            for item in data.get("scores", [])
            if "index" in item and "score" in item
        }
    except Exception as e:
        logger.warning(f"[重排]打分失败，回退向量顺序：{str(e)[:120]}")
        return docs[:top_n]

    if not scores:
        logger.warning("[重排]响应中没有有效分数，回退向量顺序")
        return docs[:top_n]

    ranked = sorted(
        ((scores.get(i, 0.0), i) for i in range(len(docs))),
        key=lambda x: x[0],
        reverse=True,
    )

    picked = [docs[i] for score, i in ranked if score >= min_score][:top_n]
    if not picked:
        # 全部低于阈值时至少返回最高分那条，避免上游拿到空结果
        picked = [docs[ranked[0][1]]]
        logger.info(f"[重排]所有片段均低于 {min_score} 分，保留最高分的 1 条")

    logger.info(
        "[重排]%d 条 -> %d 条，分数=%s",
        len(docs), len(picked), [round(s, 1) for s, _ in ranked[:len(picked)]],
    )
    return picked
