import os
from typing import Protocol, List

# Primary (Vertex) – enterprise path
from langchain_google_vertexai import VertexAIEmbeddings

# Optional (AI Studio key) – use only for local spikes
try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    HAS_GENAI = True
except Exception:
    HAS_GENAI = False


class EmbeddingsProvider(Protocol):
    def embed_documents(self, texts: List[str]) -> List[List[float]]: ...
    def embed_query(self, text: str) -> List[float]: ...


def _vertex_embeddings() -> EmbeddingsProvider:
    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    # text-embedding-004 → 768 dims
    return VertexAIEmbeddings(model_name="text-embedding-004",
                              project=project,
                              location=location)


def _genai_embeddings() -> EmbeddingsProvider:
    if not HAS_GENAI:
        raise RuntimeError(
            "langchain-google-genai not installed. pip install langchain-google-genai"
        )
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set for AI Studio key path.")
    # models/embedding-001 → 768 dims
    return GoogleGenerativeAIEmbeddings(model="models/embedding-001",
                                        google_api_key=api_key)


def get_embeddings() -> EmbeddingsProvider:
    """
    Choose embeddings backend via env:
      EMBEDDINGS_PROVIDER = "vertex" (default) | "genai"
    Env needed:
      Vertex: GOOGLE_APPLICATION_CREDENTIALS, GOOGLE_CLOUD_PROJECT, (optional) GOOGLE_CLOUD_LOCATION
      GenAI:  GOOGLE_API_KEY
    """
    provider = os.getenv("EMBEDDINGS_PROVIDER", "vertex").lower()
    if provider == "vertex":
        return _vertex_embeddings()
    elif provider in ("genai", "google"):
        return _genai_embeddings()
    else:
        raise ValueError(f"Unsupported EMBEDDINGS_PROVIDER: {provider}")
