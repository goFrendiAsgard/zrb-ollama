import os

from langchain.text_splitter import CharacterTextSplitter
from langchain.tools.retriever import create_retriever_tool
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_core.tools import BaseTool

from zrb_ollama.factory.schema import ToolFactory
from zrb_ollama.task.any_prompt_task import AnyPromptTask


def rag_tool_factory(
    name: str,
    description: str,
    doc_dir_path: str,
    db_dir_path: str,
    embeddings: Embeddings,
    chunk_size: str | int = 1000,
    chunk_overlap: str | int = 0,
) -> ToolFactory:
    def create_rag_tool(task: AnyPromptTask) -> BaseTool:
        rendered_doc_dir_path = task.render_str(doc_dir_path)
        rendered_db_dir_path = task.render_str(db_dir_path)
        doc_mtime = _get_latest_mtime(rendered_doc_dir_path)
        db_mtime = _get_latest_mtime(rendered_db_dir_path)
        if doc_mtime > db_mtime:
            _embed_docs(
                doc_dir_path=rendered_doc_dir_path,
                db_dir_path=rendered_db_dir_path,
                embeddings=embeddings,
                chunk_size=task.render_int(chunk_size),
                chunk_overlap=task.render_int(chunk_overlap),
            )
        retriever = _get_retriever(
            db_dir_path=rendered_db_dir_path, embeddings=embeddings
        )
        return create_retriever_tool(
            retriever=retriever,
            name=task.render_str(name),
            description=task.render_str(description),
        )

    return create_rag_tool


def _get_latest_mtime(dir_path) -> float:
    latest_mtime = 0
    for root, _, files in os.walk(dir_path):
        for name in files:
            filepath = os.path.join(root, name)
            mtime = os.path.getmtime(filepath)
            if mtime > latest_mtime:
                latest_mtime = mtime
    return latest_mtime


def _get_retriever(
    db_dir_path: str,
    embeddings: Embeddings,
):
    vector = FAISS.load_local(db_dir_path, embeddings)
    retriever = vector.as_retriever()
    return retriever


def _embed_docs(
    doc_dir_path: str,
    db_dir_path: str,
    embeddings: Embeddings,
    chunk_size: int = 1000,
    chunk_overlap: int = 0,
):
    all_documents = []
    for root, _, files in os.walk(doc_dir_path):
        for name in files:
            file_path = os.path.join(root, name)
            loader = TextLoader(file_path)
            file_documents = loader.load()
            all_documents += file_documents
    text_splitter = CharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    docs = text_splitter.split_documents(all_documents)
    vector = FAISS.from_documents(docs, embeddings)
    vector.save_local(db_dir_path)
