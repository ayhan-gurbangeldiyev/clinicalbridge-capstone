from langchain_chroma import Chroma

from rag.config import RETRIEVAL_K, CHROMA_COLLECTION_PREFIX
from utils.llm_client import get_embeddings


def retrieve(patient_id: str, query: str, k: int = RETRIEVAL_K, persist_dir: str = "./vectorstore") -> list[dict]:
    db = Chroma(
        collection_name=f"{CHROMA_COLLECTION_PREFIX}{patient_id}",
        embedding_function=get_embeddings(),
        persist_directory=persist_dir
    )
    results = db.similarity_search_with_relevance_scores(query, k=k)
    if not results:
        return [{"content": "NO_RELEVANT_EHR_DATA", "score": 0.0, "chunk_id": "none"}]
    return [
        {"content": doc.page_content, "score": score, "chunk_id": doc.metadata.get("chunk_index", 0)}
        for doc, score in results
    ]
