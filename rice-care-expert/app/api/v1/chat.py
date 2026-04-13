from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.rag_service import rag_expert

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat_with_expert(request: ChatRequest):
    try:
        # Gọi dịch vụ RAG đã viết ở trên
        answer = rag_expert.ask_expert(request.message)
        return {"status": "success", "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))