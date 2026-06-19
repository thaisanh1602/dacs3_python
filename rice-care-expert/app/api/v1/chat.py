from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.rag_service import rag_expert

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("")
async def chat_with_expert(request: ChatRequest):
    try:
        # Gọi dịch vụ RAG đã viết ở trên
        answer = rag_expert.ask_expert(request.message)
        return {"status": "success", "answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset-db")
async def reset_database():
    try:
        # Gọi phương thức reset và re-ingest data từ dịch vụ RAG
        result = rag_expert.reingest_and_reset()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))