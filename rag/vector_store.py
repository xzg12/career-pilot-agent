# 向量数据库服务类

import os
import threading

from dotenv import load_dotenv
load_dotenv()

from langchain_chroma import Chroma
from langchain_core.documents import Document
from utils.config_handler import chroma_conf

from model.factory import embed_model

from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.path_tool import get_abs_path
from utils.file_handler import pdf_loader, txt_loader, listdir_with_allowed_type, get_file_md5_hex
from utils.logger_handler import logger

class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=get_abs_path(chroma_conf["persist_directory"]),
            # 显式用余弦距离：chromadb 默认是 L2 平方距离，分数无上界、无法换算成相似度
            collection_metadata={"hnsw:space": "cosine"},
        )

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len,
        )

    def get_retriever(self, k: int | None = None):
        """k 用于评测或「扩大召回 + 重排」场景；不传时取配置值"""
        return self.vector_store.as_retriever(
            search_kwargs={"k": k if k is not None else chroma_conf["k"]}
        )

    def load_document(self, force: bool = False) -> dict:
        """
        从数据文件夹内读取数据文件，转为向量存入向量库
        要计算文件的MD5做去重
        :param force: True 时忽略本地 MD5 记录强制重新写入（调用方应保证 collection 已清空）
        :return: 统计信息，便于启动时展示知识库状态
        """

        def check_md5_hex(md5_for_check: str):
            if not os.path.exists(get_abs_path(chroma_conf["md5_hex_store"])):
                # 创建文件
                open(get_abs_path(chroma_conf["md5_hex_store"]), "w", encoding="utf-8").close()
                return False            # md5 没处理过

            with open(get_abs_path(chroma_conf["md5_hex_store"]), "r", encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line == md5_for_check:
                        return True     # md5 处理过

                return False            # md5 没处理过

        def save_md5_hex(md5_for_check: str):
            with open(get_abs_path(chroma_conf["md5_hex_store"]), "a", encoding="utf-8") as f:
                f.write(md5_for_check + "\n")

        def get_file_documents(read_path: str):
            lower = read_path.lower()
            # md 和 txt 都是纯文本，走同一个加载器
            if lower.endswith(("txt", "md")):
                return txt_loader(read_path)

            if lower.endswith("pdf"):
                return pdf_loader(read_path)

            return []

        stats = {"loaded": 0, "skipped": 0, "failed": 0, "chunks": 0, "files": []}

        data_path = get_abs_path(chroma_conf["data_path"])
        allowed_files_path: list[str] = listdir_with_allowed_type(
            data_path,
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        if not allowed_files_path:
            logger.warning(f"[加载知识库]{data_path} 下没有可加载的 txt/pdf 文件")
            return stats

        for path in allowed_files_path:
            # 获取文件的MD5
            md5_hex = get_file_md5_hex(path)

            if not md5_hex:
                # md5 算不出来就没法去重，直接跳过，避免重复写入
                logger.warning(f"[加载知识库]{path} 无法计算 MD5，跳过")
                stats["failed"] += 1
                continue

            if not force and check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{path}内容已经存在知识库内，跳过")
                stats["skipped"] += 1
                continue

            try:
                documents: list[Document] = get_file_documents(path)

                if not documents:
                    logger.warning(f"[加载知识库]{path}内没有有效文本内容，跳过")
                    stats["failed"] += 1
                    continue

                split_document: list[Document] = self.spliter.split_documents(documents)

                if not split_document:
                    logger.warning(f"[加载知识库]{path}分片后没有有效文本内容，跳过")
                    stats["failed"] += 1
                    continue

                batch_size = 20
                for i in range(0, len(split_document), batch_size):
                    batch = split_document[i : i + batch_size]
                    self.vector_store.add_documents(batch)

                # 记录这个已经处理好的文件的md5，避免下次重复加载
                save_md5_hex(md5_hex)

                stats["loaded"] += 1
                stats["chunks"] += len(split_document)
                stats["files"].append(os.path.basename(path))

                logger.info(f"[加载知识库]{path} 内容加载成功（{len(split_document)} 个片段）")
            except Exception as e:
                # exc_info为True会记录详细的报错堆栈，如果为False仅记录报错信息本身
                logger.error(f"[加载知识库]{path}加载失败：{str(e)}", exc_info=True)
                stats["failed"] += 1
                stats["error"] = str(e)[:300]
                continue

        logger.info(
            f"[加载知识库]完成：新增 {stats['loaded']} 个文件 / {stats['chunks']} 个片段，"
            f"跳过 {stats['skipped']} 个，失败 {stats['failed']} 个"
        )
        return stats


# ============ 知识库初始化入口（应用启动时调用） ============

_LOAD_LOCK = threading.Lock()
_KB_STATE = {"attempted": False, "stats": None}


def _classify(stats: dict) -> str:
    """根据加载结果判断知识库状态，供页面展示"""
    if stats.get("loaded", 0) > 0:
        return "ok"
    if stats.get("skipped", 0) > 0:
        return "cached"
    if stats.get("failed", 0) > 0:
        return "error"
    return "empty"


def _reset_md5_store():
    """清空 MD5 记录文件，配合强制重建使用"""
    path = get_abs_path(chroma_conf["md5_hex_store"])
    try:
        open(path, "w", encoding="utf-8").close()
    except OSError as e:
        logger.warning(f"[加载知识库]清空 MD5 记录失败：{e}")


def ensure_knowledge_loaded(force: bool = False) -> dict:
    """
    幂等地初始化求职知识库：
    - 同一进程内只真正执行一次；force=True 时强制清空 collection 并重新灌库
    - 跨进程靠 MD5 记录去重，文件没变就不会重复调用 Embedding 接口
    :return: 知识库状态统计，可直接用于页面展示
    """
    with _LOAD_LOCK:
        if _KB_STATE["attempted"] and not force:
            stats = dict(_KB_STATE["stats"] or {})
            # 保留首次加载的真实状态（ok/error/empty），避免缓存把失败原因掩盖掉
            stats.setdefault("status", "cached")
            return stats

        try:
            service = VectorStoreService()

            if force:
                try:
                    service.vector_store.delete_collection()
                    logger.info("[加载知识库]已清空原有 collection，准备重建")
                except Exception as e:
                    logger.warning(f"[加载知识库]清空 collection 失败（可能本就不存在）：{e}")
                service = VectorStoreService()
                _reset_md5_store()

            stats = service.load_document(force=force)
            stats["status"] = _classify(stats)

            # 无论成功失败都标记为已尝试，避免 Streamlit 每次 rerun 都重新请求 Embedding
            _KB_STATE["attempted"] = True
            _KB_STATE["stats"] = dict(stats)
            return stats

        except Exception as e:
            logger.error(f"[加载知识库]初始化失败：{str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "loaded": 0,
                "skipped": 0,
                "failed": 0,
                "chunks": 0,
                "files": [],
            }


if __name__ == '__main__':
    print(ensure_knowledge_loaded())

    vs = VectorStoreService()

    retriever = vs.get_retriever()

    res = retriever.invoke("迷路")
    for r in res:
        print(r.page_content)
        print("-"*20)
