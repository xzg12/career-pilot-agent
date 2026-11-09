import os
from langchain_chroma import Chroma
from langchain_core.documents import Document
from model.factory import embed_model
from utils.config_handler import chroma_conf
from utils.path_tool import get_abs_path


CANDIDATE_COLLECTION = "candidate_profile"
JOB_COLLECTION = "job_jd"

# 显式指定余弦距离。Chromadb 默认是 L2 平方距离，那样 similarity_search_with_score
# 返回的分数没有上界，也无法用 1 - distance 换算成相似度。
# 注意：space 在 collection 创建时确定，已存在的 collection 不会被改写，需要删库重建。
COLLECTION_METADATA = {"hnsw:space": "cosine"}


def _get_chroma(collection_name):
    return Chroma(
        collection_name=collection_name,
        embedding_function=embed_model,
        persist_directory=get_abs_path(chroma_conf["persist_directory"]),
        collection_metadata=COLLECTION_METADATA,
    )


def _to_similarity(distance) -> float:
    """把 Chroma 的余弦距离 [0,2] 转成相似度 [0,1]，越小越远"""
    return round(max(0.0, min(1.0, 1.0 - float(distance))), 4)


def reset_match_collections():
    """删除匹配用的两个 collection，下次同步时会按 cosine 重新创建"""
    removed = []
    for name in (CANDIDATE_COLLECTION, JOB_COLLECTION):
        try:
            _get_chroma(name).delete_collection()
            removed.append(name)
        except Exception:
            pass
    return f"已重置 collection：{', '.join(removed) if removed else '无'}"


def sync_candidate_to_vector():
    from career_store import get_profile
    profile = get_profile()
    if not profile:
        return "候选人资料为空，请先填写"
    vs = _get_chroma(CANDIDATE_COLLECTION)
    vs.delete_collection()
    vs = _get_chroma(CANDIDATE_COLLECTION)
    chunks = []
    skills = profile.get("skills", "")
    if skills:
        chunks.append(Document(
            page_content=f"候选人技能：{skills}",
            metadata={"source": "profile", "type": "skills"}
        ))
    summary = profile.get("resume_summary", "")
    if summary:
        for i in range(0, len(summary), 300):
            chunk_text = summary[i:i+300]
            if chunk_text.strip():
                chunks.append(Document(
                    page_content=f"简历摘要：{chunk_text}",
                    metadata={"source": "profile", "type": "resume_summary", "chunk": i//300}
                ))
    target_roles = profile.get("target_roles", "")
    if target_roles:
        chunks.append(Document(
            page_content=f"目标岗位方向：{target_roles}",
            metadata={"source": "profile", "type": "target_roles"}
        ))
    if chunks:
        vs.add_documents(chunks)
    return f"已同步 {len(chunks)} 个候选人资料向量块"


def sync_job_to_vector(job_id=None):
    from career_store import list_jobs, get_job
    vs = _get_chroma(JOB_COLLECTION)
    if job_id:
        jobs = [get_job(job_id)]
        if not jobs or not jobs[0]:
            return f"未找到岗位 ID={job_id}"
    else:
        jobs = list_jobs()
    if not jobs:
        return "没有岗位可同步"
    chunks = []
    ids = []
    for job in jobs:
        jid = str(job["id"])
        desc = job.get("description", "")
        if not desc:
            continue
        for i in range(0, len(desc), 300):
            chunk_text = desc[i:i+300]
            if chunk_text.strip():
                chunks.append(Document(
                    page_content=f"{job['company']} - {job['title']}：{chunk_text}",
                    metadata={"source": "job", "job_id": jid, "company": job.get("company", ""), "title": job.get("title", ""), "chunk": i//300}
                ))
                # 用确定性 ID，重复同步时覆盖而不是重复追加
                ids.append(f"job_{jid}_chunk_{i//300}")
    if chunks:
        vs.add_documents(chunks, ids=ids)
    return f"已同步 {len(chunks)} 个岗位描述向量块"


def vector_match_evidence(query, top_k=5):
    candidate_vs = _get_chroma(CANDIDATE_COLLECTION)
    job_vs = _get_chroma(JOB_COLLECTION)
    candidate_docs = candidate_vs.similarity_search_with_score(query, k=top_k)
    job_docs = job_vs.similarity_search_with_score(query, k=top_k)
    evidence = []
    for doc, score in candidate_docs:
        evidence.append({
            "source": "候选人资料",
            "content": doc.page_content,
            "type": doc.metadata.get("type", ""),
            "similarity": _to_similarity(score)
        })
    for doc, score in job_docs:
        evidence.append({
            "source": f"岗位：{doc.metadata.get('company', '')} - {doc.metadata.get('title', '')}",
            "content": doc.page_content,
            "type": "job_jd",
            "similarity": _to_similarity(score)
        })
    evidence.sort(key=lambda x: x["similarity"], reverse=True)
    return evidence[:top_k]


def rerank_with_llm(query, evidence_list):
    from model.factory import chat_model
    from langchain_core.output_parsers import StrOutputParser
    from langchain_core.prompts import PromptTemplate
    prompt_text = """你是一个岗位匹配重排助手。根据查询和候选证据，对证据进行相关性排序并打分。

查询：{query}

候选证据：
{evidence_text}

请以 JSON 格式返回重排结果：
{{
  "ranked_evidence": [
    {{"index": 0, "relevance_score": 10, "reason": "相关性原因"}},
    {{"index": 1, "relevance_score": 7, "reason": "相关性原因"}}
  ],
  "match_summary": "一句话总结匹配情况"
}}

要求：
1. relevance_score 为 1-10 分
2. 按相关性从高到低排序
3. reason 简短说明为什么相关
4. 只输出 JSON"""
    evidence_text = ""
    for i, e in enumerate(evidence_list):
        evidence_text += f"\n[{i}] 来源：{e['source']} | 内容：{e['content'][:200]}"
    prompt = PromptTemplate.from_template(prompt_text)
    chain = prompt | chat_model | StrOutputParser()
    result_str = chain.invoke({"query": query, "evidence_text": evidence_text})
    import json
    try:
        start = result_str.find("{")
        end = result_str.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(result_str[start:end])
            return parsed
    except json.JSONDecodeError:
        pass
    return {"ranked_evidence": [], "match_summary": result_str[:200]}
