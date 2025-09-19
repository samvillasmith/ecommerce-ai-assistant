# backend/services/gemini_chain.py
import os
import re
from typing import List, Tuple

import google.generativeai as genai
from dotenv import load_dotenv

# Your vector store should expose `vectorstore` (e.g., PineconeVectorStore)
from backend.services.vector_store import vectorstore

load_dotenv()


# ---------- price helpers (fallback if price_display missing) ----------
def _format_price(value, currency: str = "$") -> str | None:
    """Interpret ints like 5499 as cents -> $54.99; floats as dollars."""
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
            return f"{currency}{(value / 100.0):,.2f}"
        if isinstance(value, float):
            return f"{currency}{value:,.2f}"
        return None
    except Exception:
        return None


def _price_from_md(md: dict) -> str:
    if not md:
        return "N/A"
    if md.get("price_display"):
        return str(md["price_display"])
    p = _format_price(md.get("price"))
    return p or "N/A"


# ---------- query helpers ----------
_LISTY = re.compile(r"\b(all|list|others?|more|everything)\b", re.I)

def _extract_brand_hint(text: str) -> str | None:
    """
    Super-light brand extraction: take the longest capitalized token/phrase,
    or known brand words in the query. This is heuristic but good enough here.
    """
    candidates = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b", text)
    if not candidates:
        # also catch lowercase brand names we expect
        for w in ("nike", "vans", "adidas", "converse", "new balance", "on running"):
            if w in text.lower():
                return w.title()
        return None
    # Prefer the longest candidate (e.g., "New Balance" over "New")
    return max(candidates, key=len)


# ---------- prompt ----------
SYSTEM_MESSAGE = (
    "You are a helpful shop assistant. Answer only about the shop's product catalog. "
    "When you list products, use the items given in Context. "
    "If the question asks for 'all' or 'others', enumerate all items found in Context, "
    "one per line. If you don't know, say: 'I can only help with product-related queries.' "
    "Use the 'Price' exactly as shown in Context (do not invent or reformat)."
)


# ---------- context building ----------
def _hit_to_row(hit) -> dict:
    md = getattr(hit, "metadata", {}) or {}
    return {
        "name": md.get("name") or md.get("ProductName") or "N/A",
        "brand": md.get("brand") or md.get("ProductBrand") or "N/A",
        "gender": md.get("gender") or md.get("Gender") or "N/A",
        "color": md.get("primaryColor") or md.get("PrimaryColor") or "N/A",
        "price": _price_from_md(md),
        "description": getattr(hit, "page_content", "") or md.get("description") or "",
    }


def _get_context(query: str) -> str:
    """Retrieve multiple results and shape them for listing answers."""
    try:
        # Pull several candidates so we can enumerate
        hits = vectorstore.similarity_search(query, k=10)
    except Exception:
        return "No relevant context found."

    if not hits:
        return "No relevant context found."

    rows = [_hit_to_row(h) for h in hits]

    # If user hints a brand, keep only that brand (case-insensitive)
    brand_hint = _extract_brand_hint(query)
    if brand_hint:
        rows = [r for r in rows if r["brand"].lower() == brand_hint.lower()] or rows

    # Dedupe by (brand, name) while preserving order
    seen = set()
    unique: List[dict] = []
    for r in rows:
        key = (r["brand"].lower(), r["name"].lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)

    # If user asked for “all/list/others/more” keep as many as we have,
    # otherwise keep the top 3 to stay concise.
    want_all = bool(_LISTY.search(query))
    max_items = len(unique) if want_all else min(3, len(unique))
    items = unique[:max_items]

    # Build a list-style context the model can echo reliably.
    # We include a flat header too for fallback single-item answers.
    lines = ["Items:"]
    for r in items:
        lines.append(
            f"- {r['brand']} {r['name']} ({r['color']}, {r['gender']}), Price: {r['price']}\n  {r['description']}"
        )

    # Also include a compact table-like summary to bias enumeration
    lines.append("\nSummary:")
    for r in items:
        lines.append(f"{r['brand']} | {r['name']} | {r['color']} | {r['gender']} | {r['price']}")

    return "\n".join(lines)


# ---------- main generate function ----------
def generate_response(query: str, history: List[str]) -> Tuple[str, List[str]]:
    """
    Returns (assistant_text, new_history).
    - Pulls multiple Pinecone results so 'list all X' works.
    - Does not mutate the input history.
    - Uses GOOGLE_API_KEY (AI Studio key).
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set.")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-1.5-flash")

    context = _get_context(query)

    prompt = "\n".join(
        [
            SYSTEM_MESSAGE,
            "",
            "Conversation:",
            *history,
            f"User: {query}",
            "",
            "Context:",
            context,
            "",
            "Assistant:",
        ]
    )

    resp_text = model.generate_content(prompt).text or ""
    clean = resp_text.strip()
    new_history = [*history, f"User: {query}", f"Assistant: {clean}"]
    return clean, new_history
