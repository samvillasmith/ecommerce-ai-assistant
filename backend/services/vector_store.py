# backend/services/vector_store.py
import os

# Only load .env during normal runtime, not during pytest (so tests can fully control env)
if os.getenv("PYTEST_CURRENT_TEST") is None:
    from dotenv import load_dotenv
    load_dotenv()

from pinecone import Pinecone
from langchain_pinecone import PineconeVectorStore

# Embedding backends
from langchain_google_vertexai import VertexAIEmbeddings
try:
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    HAS_GENAI = True
except Exception:
    HAS_GENAI = False

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "ecommerce-ai-assistant")
NAMESPACE = os.getenv("PINECONE_NAMESPACE", "") or None

provider = os.getenv("EMBEDDINGS_PROVIDER", "vertex").lower()

if provider == "vertex":
    # explicit check so tests (and prod) fail fast if not set
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        raise KeyError("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    embeddings = VertexAIEmbeddings(
        model_name="text-embedding-004",
        project=project,
        location=location,
    )

elif provider in ("genai", "google"):
    if not HAS_GENAI:
        raise RuntimeError("langchain-google-genai not installed. pip install langchain-google-genai")
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set.")
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key,
    )

else:
    raise ValueError(f"Unsupported EMBEDDINGS_PROVIDER: {provider}")

# Pinecone client (requires PINECONE_API_KEY)
pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

# Reuse existing index created by your sync script
vectorstore = PineconeVectorStore.from_existing_index(
    index_name=INDEX_NAME,
    embedding=embeddings,
    namespace=NAMESPACE,
    text_key="description",
)
