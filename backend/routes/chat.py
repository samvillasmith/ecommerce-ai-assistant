from fastapi import APIRouter 
from pydantic import BaseModel
from typing import List, Optional
from backend.services.gemini_chain import generate_response

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    history: List[str] = []

@router.post("/chat")
def chat(request: ChatRequest):
    response, history = generate_response(request.query, request.history)
    return {"response": response, "history": history}
