# 文件处理工具

import os,hashlib
from utils.logger_handler import logger


from langchain_core.documents import Document

def get_file_md5_hex(filepath:str):         # 获取文件的md5的十六进制字符串
    if not os.path.exists(filepath):
        logger.error(f"[MD5计算]文件{filepath}不存在")
        return
    if not os.path.isfile(filepath):
        logger.error(f"[MD5计算]路径{filepath}不是文件")
        return

    md5_obj = hashlib.md5()
    chunk_size=4096     # 4KB分片，避免文件过大爆内存
    try:
            with open(filepath, "rb")as f:  # 必须二进制读取
                while chunk:=f.read(chunk_size):
                    md5_obj.update(chunk)

            md5_hex=md5_obj.hexdigest()
            return md5_hex
    except Exception as  e:
        logger.error(f"计算文件{filepath}md5失败，{str(e)}")
        return None

def listdir_with_allowed_type(path:str,allowed_types:tuple[str]):   # 递归返回目录下允许类型的文件路径
    """递归遍历子目录，便于知识库按主题（resume/interview/job/process）分类组织。

    返回排序后的元组，保证每次加载顺序一致，日志与 MD5 去重结果可复现。
    """
    files= []
    if not os.path.isdir(path):
        logger.error(f"[lisdir_with_allowed_type]{path}不是文件夹")
        return tuple(files)     # 目录不存在时返回空元组，避免调用方把类型列表当成文件路径遍历

    allowed = tuple(t.lower() for t in allowed_types)
    for root, _dirs, names in os.walk(path):
        for name in names:
            if name.lower().endswith(allowed):
                files.append(os.path.join(root, name))
    return tuple(sorted(files))

def pdf_loader(filepath:str,passwd=None)->list[Document]:
    """逐页解析 PDF，返回每页一个 Document（替代 langchain_community 的 PyPDFLoader）。

    metadata 结构与原实现保持一致：{'source': 路径, 'page': 页码}，
    因为 rag_service 依赖 source 字段标注引用来源。
    """
    # PyMuPDF >= 1.24 的官方模块名是 pymupdf，旧名 fitz 已标记弃用
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz

    docs: list[Document] = []
    doc = fitz.open(filepath)
    try:
        if doc.is_encrypted and not doc.authenticate(passwd or ""):
            raise ValueError(f"PDF 已加密且未提供正确密码：{filepath}")
        for page_no, page in enumerate(doc):
            text = page.get_text().strip()
            if text:
                docs.append(Document(
                    page_content=text,
                    metadata={"source": filepath, "page": page_no},
                ))
    finally:
        doc.close()
    return docs

def txt_loader(filepath:str)->list[Document]:
    """整文件读取为单个 Document（替代 langchain_community 的 TextLoader）。

    errors="replace" 而非直接抛异常：知识库文档来源杂，个别非法字节不应导致整批灌库失败。
    """
    with open(filepath, encoding="utf-8", errors="replace") as f:
        text = f.read()
    return [Document(page_content=text, metadata={"source": filepath})]