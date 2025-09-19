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
EMBEDDING_DIM = 768  # text-embedding-004 & models/embedding-001 -> 768 dims
PINECONE_INDEX = os.getenv("PINECONE_INDEX_NAME", "ecommerce-ai-assistant")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")


# --- price normalization (same rule as gemini_chain) --------------------------
def _format_price(value, currency: str = "$") -> str | None:
    if value is None:
        return None
    try:
        if isinstance(value, str):
            s = value.strip()
            if s.replace(".", "", 1).isdigit():
                value = float(s) if "." in s else int(s)
            else:
                return None
        if isinstance(value, int):
            dollars = value / 100.0
            return f"{currency}{dollars:,.2f}"
        if isinstance(value, float):
            return f"{currency}{value:,.2f}"
        return None
    except Exception:
        return None


def ensure_pinecone_index(pc: Pinecone, index_name: str, dimension: int):
    spec = ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION)
    exists = any(i["name"] == index_name for i in pc.list_indexes())
    if not exists:
        pc.create_index(name=index_name, dimension=dimension, metric="cosine", spec=spec)

    while not pc.describe_index(index_name).status["ready"]:
        print(f"Please stand by. The pinecone index {index_name} is preparing.")
        time.sleep(5)

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
    """
    Build a clean text string from product fields.
    Filters out None/empty values and avoids double spaces.
    """
    fields = [
        row.get("name"),
        row.get("brand"),
        row.get("gender"),
        row.get("primaryColor"),
        row.get("description"),
        row.get("price"),
    ]
    # filter out None/empty, strip each, then join
    return " ".join(str(f).strip() for f in fields if f and str(f).strip())


def main():
    pinecone_api_key = os.getenv("PINECONE_API_KEY")
    if not pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is not set.")
    pc = Pinecone(api_key=pinecone_api_key)

    idx = ensure_pinecone_index(pc, PINECONE_INDEX, EMBEDDING_DIM)

    embed = get_embeddings()

    # Preflight embed call
    try:
        _ = embed.embed_documents(["ping"])
    except Exception as e:
        raise RuntimeError(f"Embedding preflight failed: {e}")

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

        metas = []
        for _, row in batch.iterrows():
            metas.append(
                {
                    "id": row.get("id"),
                    "name": row.get("name"),
                    "description": row.get("description"),
                    "brand": row.get("brand"),
                    "gender": row.get("gender"),
                    "price": row.get("price"),
                    "price_display": _format_price(row.get("price")),  # formatted copy
                    "primaryColor": row.get("primaryColor"),
                }
            )

        payload = list(zip(ids, vectors, metas))
        idx.upsert(vectors=payload)
        time.sleep(0.5)  # gentle pacing

    print("Pinecone sync complete ✅")


if __name__ == "__main__":
    main()
