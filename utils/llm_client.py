import os


class LocalEmbeddings:
    """LangChain-compatible embeddings backed by ChromaDB's built-in local model
    (all-MiniLM-L6-v2 via onnxruntime). Requires no API key or embedding
    deployment — useful when the Azure resource has no embedding model.
    """

    def __init__(self):
        from chromadb.utils import embedding_functions
        self._ef = embedding_functions.DefaultEmbeddingFunction()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in vec] for vec in self._ef(texts)]

    def embed_query(self, text: str) -> list[float]:
        return [float(x) for x in self._ef([text])[0]]


def get_llm(temperature: float = 0):
    if os.environ.get("USE_AZURE", "true").lower() == "true":
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_KEY"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
            temperature=temperature,
        )
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            api_key=os.environ["OPENAI_API_KEY"],
            temperature=temperature,
        )


def get_embeddings():
    if os.environ.get("USE_LOCAL_EMBEDDINGS", "false").lower() == "true":
        return LocalEmbeddings()
    if os.environ.get("USE_AZURE", "true").lower() == "true":
        from langchain_openai import AzureOpenAIEmbeddings
        return AzureOpenAIEmbeddings(
            azure_deployment=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_KEY"],
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        )
    else:
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            api_key=os.environ["OPENAI_API_KEY"],
        )
