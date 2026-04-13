import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import chat, predict
from app.core.config import settings


def get_application() -> FastAPI:
    # 1. Khởi tạo FastAPI app với các thông tin cấu hình từ core/config.py
    _app = FastAPI(
        title="Rice Care Expert API",
        description="Hệ thống AI chuyên gia hỗ trợ kỹ thuật canh tác và chẩn đoán bệnh lúa",
        version="1.0.0",
    )

    # 2. Cấu hình CORS (Cho phép App Android hoặc Frontend gọi API)
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Trong thực tế nên giới hạn domain cụ thể
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 3. Đăng ký các Router (Endpoints)
    # Route cho chatbot RAG
    _app.include_router(
        chat.router,
        prefix="/api/v1/chat",
        tags=["Expert Chatbot"]
    )

    # Route cho nhận diện bệnh qua hình ảnh
    _app.include_router(
        predict.router,
        prefix="/api/v1/predict",
        tags=["Disease Prediction"]
    )

    return _app


app = get_application()


@app.get("/", tags=["Health Check"])
async def root():
    return {
        "status": "active",
        "message": "Chào mừng đến với Rice Care Expert API",
        "docs": "/docs"
    }


# Chạy server trực tiếp bằng lệnh: python app/main.py
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )