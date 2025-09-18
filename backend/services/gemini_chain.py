import os 
import google.generativeai as genai
from dotenv import load_dotenv
from backend.services.vector_store import VectorStore 

load_dotenv() 
system_message = (
    "You are a helpful assistant that provides accurate and concise information about products in the online store. " \
    "Your specialty is to answer questions related to the product details, availability, and recommendations based " \
    "on the context given. If you don't know the answer, just say that you don't know, don't try to make up an answer."
)

def get_relevant_context(query):
    results = VectorStore.similarity_search(query, k=1)
    if results:
        metadata = results[0].metadata 
        return (
            f"Product Name: {metadata.get('product_name', 'N/A')}\n"
            f"Brand: {metadata.get('brand', 'N/A')}\n"
            f"Price: {metadata.get('price', 'N/A')}\n"
            f"Gender: {metadata.get('gender', 'N/A')}\n"
            f"Color: {metadata.get('color', 'N/A')}\n"
            f"Description: {results[0].page_content}\n"
        )
    return "No relevant context found."
def generate_response():
    pass

