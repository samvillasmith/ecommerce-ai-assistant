# embedding/sync_pinecone.py
import os
import time
import asyncio
import pandas as pd
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from tqdm.auto import tqdm
from prisma import Prisma

from providers.embeddings import get_embeddings

load_dotenv()

# --- constants ---
EMBEDDING_DIM = 768  # text-embedding-004 (Vertex) and models/embedding-001 (GenAI) are 768
PINECONE_INDEX = os.getenv("PINECONE_INDEX_NAME", "ecommerce-ai-assistant")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")


def ensure_pinecone_index(pc: Pinecone, index_name: str, dimension: int):
    spec = ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION)

    exists = any(i["name"] == index_name for i in pc.list_indexes())
    if not exists:
        pc.create_index(name=index_name, dimension=dimension, metric="cosine", spec=spec)
    # Wait until ready
    while not pc.describe_index(index_name).status["ready"]:
        print(f"Please stand by. The pinecone index {index_name} is preparing.")
        time.sleep(5)

    # Verify dimension matches (cannot change after creation)
    desc = pc.describe_index(index_name)
    if desc.dimension != dimension:
        raise RuntimeError(
            f"Existing Pinecone index '{index_name}' has dimension={desc.dimension}, "
            f"but your embedding model outputs dimension={dimension}. "
            f"Create a new index or recreate this one with the correct dimension."
        )
    return pc.Index(index_name)


async def fetch_products_df() -> pd.DataFrame:
    db = Prisma()
    await db.connect()
    products = await db.product.find_many()
    df = pd.DataFrame([p.model_dump() for p in products])
    await db.disconnect()
    return df


def safe(val):  # None-safe str()
    return "" if val is None else str(val)


def build_text(row: dict) -> str:
    parts = [
        safe(row.get("description")),
        safe(row.get("name")),
        safe(row.get("brand")),
        safe(row.get("gender")),
        safe(row.get("price")),
        safe(row.get("primaryColor")),
    ]
    # drop empty strings and normalize any stray whitespace
    return " ".join(p for p in parts if p).strip()

def main():
    # Pinecone client
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    if not pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is not set.")
    pc = Pinecone(api_key=pinecone_api_key)

    # Ensure index
    idx = ensure_pinecone_index(pc, PINECONE_INDEX, EMBEDDING_DIM)

    # Embeddings provider (Vertex by default; switch with EMBEDDINGS_PROVIDER=genai)
    embed = get_embeddings()

    # Preflight
    try:
        _ = embed.embed_documents(["ping"])
    except Exception as e:
        raise RuntimeError(f"Embedding preflight failed: {e}")

    # Data
    df = asyncio.run(fetch_products_df())
    if df.empty:
        print("No data found in products; nothing to sync.")
        return

    batch_size = int(os.getenv("EMBED_BATCH_SIZE", "32"))
    total_batches = (len(df) + batch_size - 1) // batch_size

    for start in tqdm(range(0, len(df), batch_size), desc="Syncing with Pinecone", unit="batch", total=total_batches):
        end = min(len(df), start + batch_size)
        batch = df.iloc[start:end]

        ids = [str(row["id"]) for _, row in batch.iterrows()]
        texts = [build_text(row) for _, row in batch.iterrows()]
        vectors = embed.embed_documents(texts)

        metas = [
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "description": row.get("description"),
                "brand": row.get("brand"),
                "gender": row.get("gender"),
                "price": row.get("price"),
                "primaryColor": row.get("primaryColor"),
            }
            for _, row in batch.iterrows()
        ]

        payload = list(zip(ids, vectors, metas))
        idx.upsert(vectors=payload)
        time.sleep(0.5)  # gentle pacing

    print("Pinecone sync complete ✅")


if __name__ == "__main__":
    main()
