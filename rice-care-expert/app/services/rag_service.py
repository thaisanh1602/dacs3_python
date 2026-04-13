import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
# from langchain_community.vectorstores import Chroma
# SỬA DÒNG NÀY:
from langchain_classic.chains.retrieval_qa.base import RetrievalQA
from langchain_core.prompts import PromptTemplate

# Xác định đường dẫn gốc
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class RAGService:
    def __init__(self):
        # Đường dẫn tới vector_db theo cấu trúc ảnh của bạn
        VECTOR_DB_DIR = BASE_DIR / "vector_db"

        # 1. Khởi tạo Embedding miễn phí
        self.embeddings = HuggingFaceEmbeddings(model_name="keepitreal/vietnamese-sbert")

        # 2. Kết nối tới Vector DB
        if not VECTOR_DB_DIR.exists():
            print(f"⚠️ Cảnh báo: Thư mục {VECTOR_DB_DIR} chưa tồn tại. Hãy chạy ingest_to_vector.py trước!")

        self.vector_db = Chroma(
            persist_directory=str(VECTOR_DB_DIR),
            embedding_function=self.embeddings
        )

        # 3. Cấu hình Prompt chuyên gia lúa gạo
        template = """Bạn là một chuyên gia về cây lúa tại Việt Nam.
        Sử dụng thông tin dưới đây để trả lời câu hỏi. 
        Nếu thông tin không có trong tài liệu, hãy nói 'Tôi chưa có dữ liệu cụ thể về vấn đề này'.

        Tài liệu: {context}
        Câu hỏi: {question}

        Trả lời (Chia rõ: Triệu chứng, Nguyên nhân, Cách xử lý):"""

        self.prompt = PromptTemplate(template=template, input_variables=["context", "question"])

        # 4. LLM (Dùng GPT-4o để tổng hợp câu trả lời)
        self.llm = ChatGroq(
            temperature=0,
            model_name="llama-3.1-8b-instant",  # Mô hình rất thông minh
            groq_api_key=os.getenv("GROQ_API_KEY")  # Dán key Groq vào đây hoặc để trong .env
        )

    def ask_expert(self, query: str):
        # Tạo chuỗi xử lý RAG
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vector_db.as_retriever(search_kwargs={"k": 3}),
            chain_type_kwargs={"prompt": self.prompt}
        )
        result = qa_chain.invoke({"query": query})
        return result["result"]


# Khởi tạo instance dùng chung
rag_expert = RAGService()