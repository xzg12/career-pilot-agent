"""模型工厂：统一通过 DashScope 的 OpenAI 兼容接口调用。

为什么不再用 ChatTongyi / DashScopeEmbeddings：
`langchain-community` 已被官方标记为 sunset（停止维护），导入时会打 DeprecationWarning。
OpenAI 兼容接口是事实标准，换供应商只需改 config/rag.yml 里的 base_url，代码不用动。

注意：本文件只换传输协议，模型本身仍是 qwen-plus / qwen3-vl-plus / text-embedding-v4。
实测兼容接口返回的 embedding 与原生接口余弦相似度 1.000000，已有向量库无需重建。
"""
import os
from abc import ABC, abstractmethod
from typing import Optional

from dotenv import load_dotenv
load_dotenv()       # 模型工厂被任何入口导入时都能读到 .env 里的 DASHSCOPE_API_KEY

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from utils.config_handler import rag_conf

BASE_URL = rag_conf.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
TIMEOUT = rag_conf.get("timeout", 120)
EMBED_BATCH = rag_conf.get("embedding_batch_size", 10)


def _api_key() -> str:
    key = os.getenv("DASHSCOPE_API_KEY")
    if not key:
        raise RuntimeError(
            "未找到 DASHSCOPE_API_KEY，请在项目根目录的 .env 中配置后重试"
        )
    return key


class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        pass


class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return ChatOpenAI(
            model=rag_conf["chat_model_name"],
            base_url=BASE_URL,
            api_key=_api_key(),
            timeout=TIMEOUT,
        )


class VisionModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return ChatOpenAI(
            model=rag_conf["vision_model_name"],
            base_url=BASE_URL,
            api_key=_api_key(),
            timeout=TIMEOUT,
        )


class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return OpenAIEmbeddings(
            model=rag_conf["embedding_model_name"],
            base_url=BASE_URL,
            api_key=_api_key(),
            timeout=TIMEOUT,
            # DashScope 不是 OpenAI 自家模型，不能让 SDK 用 tiktoken 预估长度并截断，
            # 否则中文长文本会在客户端被静默裁掉
            check_embedding_ctx_length=False,
            # OpenAIEmbeddings 默认 chunk_size=1000，而 text-embedding-v4 单批最多 10 条
            chunk_size=EMBED_BATCH,
        )


chat_model = ChatModelFactory().generator()
vision_model = VisionModelFactory().generator()
embed_model = EmbeddingsFactory().generator()
