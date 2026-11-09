from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
import threading

from rag.vector_store import VectorStoreService
from rag.reranker import rerank_documents
from utils.prompt_loader import load_rag_prompts
from utils.config_handler import chroma_conf
from utils.logger_handler import logger
from langchain_core.prompts import PromptTemplate
from model.factory import chat_model


EMPTY_CONTEXT_REPLY = (
    "【知识库无检索结果】知识库中没有检索到与「{query}」相关的内容，"
    "请勿凭空作答，如实告知用户知识库暂无相关资料，并建议补充 data/career 目录下的文档后重建知识库。"
)

RETRIEVAL_ERROR_REPLY = (
    "【知识库检索失败】{error}。请勿凭空作答，如实告知用户知识库暂时不可用"
    "（可能是 Embedding 额度或网络问题），并建议其检查后在侧边栏点击「重建知识库」重试。"
)


class RagSummarizeService:
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.retriever = self.vector_store.get_retriever()
        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()

    def _init_chain(self):
        return self.prompt_template | self.model | StrOutputParser()

    def retriever_docs(self, query: str, k: int | None = None) -> list[Document]:
        """k 不传时用配置值；评测和「扩大召回 + 重排」会显式指定"""
        if k is None:
            return self.retriever.invoke(query)
        return self.vector_store.get_retriever(k).invoke(query)

    def retrieve_with_rerank(
        self,
        query: str,
        recall_k: int | None = None,
        top_n: int | None = None,
    ) -> list[Document]:
        """扩大召回后用 LLM 重排，返回最相关的 top_n 条"""
        recall_k = recall_k if recall_k is not None else chroma_conf.get("rerank_recall_k", 8)
        top_n = top_n if top_n is not None else chroma_conf.get("rerank_top_n", chroma_conf["k"])
        candidates = self.retriever_docs(query, k=recall_k)
        return rerank_documents(query, candidates, top_n=top_n)

    def _retrieve_for_answer(self, query: str) -> list[Document]:
        if chroma_conf.get("rerank_enabled", False):
            return self.retrieve_with_rerank(query)
        return self.retriever_docs(query)

    def rag_summarize(self, query: str) -> str:

        try:
            context_docs = self._retrieve_for_answer(query)
        except Exception as e:
            # 检索本身也要调 Embedding，额度/网络异常时不能把异常抛给 Agent 工具
            logger.error(f"[RAG检索]向量检索失败：{str(e)}", exc_info=True)
            return RETRIEVAL_ERROR_REPLY.format(error=str(e)[:120])

        # 检索为空时不再调用 LLM：既省一次接口调用，也避免模型在没有依据的情况下编造
        if not context_docs:
            logger.warning(f"[RAG检索]未命中任何片段，query={query}")
            return EMPTY_CONTEXT_REPLY.format(query=query)

        context = ""
        for counter, doc in enumerate(context_docs, 1):
            source = doc.metadata.get("source", "未知来源")
            context += f"[参考资料{counter}]: {doc.page_content}（来源：{source}）\n"

        try:
            logger.info(f"[RAG检索]命中 {len(context_docs)} 个片段，query={query}")
            return self.chain.invoke(
                {
                    "input": query,
                    "context": context,
                }
            )
        except Exception as e:
            logger.error(f"[RAG检索]总结生成失败：{str(e)}", exc_info=True)
            return f"【知识库回答生成失败】{str(e)[:120]}。检索已命中 {len(context_docs)} 个片段，但总结阶段模型调用失败，请稍后重试。"


# ============ 进程级单例 ============

_SERVICE = None
_SERVICE_LOCK = threading.Lock()


def get_rag_service() -> RagSummarizeService:
    """复用同一个 RAG 服务实例，避免每次工具调用都重建 Chroma 连接"""
    global _SERVICE
    if _SERVICE is None:
        with _SERVICE_LOCK:
            if _SERVICE is None:
                _SERVICE = RagSummarizeService()
    return _SERVICE


def reset_rag_service():
    """知识库重建后调用，让下一次检索重新绑定新的 collection"""
    global _SERVICE
    with _SERVICE_LOCK:
        _SERVICE = None


if __name__ == '__main__':
    rag = get_rag_service()
    print(rag.rag_summarize("AI应用开发岗位需要哪些技能"))
