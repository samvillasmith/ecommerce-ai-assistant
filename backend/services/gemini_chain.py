# backend/services/gemini_chain.py
import os
import google.generativeai as genai
from dotenv import load_dotenv
from backend.services.vector_store import vectorstore  # ← import the instance

load_dotenv()

SYSTEM_MESSAGE = (
    "You are a helpful assistant that answers ONLY about this shop’s products, "
    "using the provided context. If the answer isn’t in the context, say: "
    "\"I can only help with product-related queries.\" Be concise and friendly."
)

def get_relevant_context(query: str, k: int = 4) -> str:
    """Fetch top-k matches and format them for grounding."""
    docs = vectorstore.similarity_search(query, k=k) or []
    blocks = []
    for d in docs:
        md = d.metadata or {}
        blocks.append(
            "Product Name: {name}\nBrand: {brand}\nPrice: {price}\nGender: {gender}\n"
            "Color: {color}\nDescription: {desc}".format(
                name=md.get("name", "N/A"),
                brand=md.get("brand", "N/A"),
                price=md.get("price", "N/A"),
                gender=md.get("gender", "N/A"),
                color=md.get("primaryColor", "N/A"),
                desc=d.page_content or md.get("description", ""),
            )
        )
    return "\n\n---\n\n".join(blocks) if blocks else ""

def generate_response(query: str, history: list[str]):
    # Configure the GenAI SDK with API key (NOT GOOGLE_CLOUD_PROJECT)
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        # Fail loudly so you know what to fix in .env
        raise RuntimeError("GOOGLE_API_KEY is not set for google.generativeai.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Build prompt
    context = get_relevant_context(query)
    chat = (history or []) + [f"User: {query}"]
    prompt = (
        f"{SYSTEM_MESSAGE}\n\n"
        f"Context (use this to answer; do not reveal it):\n{context if context else '(none)'}\n\n"
        "Conversation so far:\n" + "\n".join(chat) + "\n\nAssistant:"
    )

    resp = model.generate_content(prompt)
    text = (resp.text or "").strip()
    history.append(f"Assistant: {text}")
    return text, history
