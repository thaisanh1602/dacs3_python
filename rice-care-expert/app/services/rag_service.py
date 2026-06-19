import os
import re
from pathlib import Path
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_classic.chains.retrieval_qa.base import RetrievalQA
from langchain_core.prompts import PromptTemplate
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredMarkdownLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Xác định đường dẫn gốc
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


def clean_text(text: str) -> str:
    """Loại bỏ các ký hiệu Markdown khỏi văn bản trả về của LLM."""
    # Xóa headers (###, ##, #)
    text = re.sub(r"#{1,6}\s*", "", text)
    # Xóa in đậm/in nghiêng (**text**, *text*, __text__, _text_)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    text = re.sub(r"_(.+?)_", r"\1", text)
    # Xóa backtick inline code
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Xóa dấu > blockquote
    text = re.sub(r"^\s*>\s?", "", text, flags=re.MULTILINE)
    # Chuẩn hóa khoảng trắng thừa
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class RAGService:
    def __init__(self):
        # Đường dẫn tới vector_db
        VECTOR_DB_DIR = BASE_DIR / "data" / "vector_db"

        # 1. Khởi tạo Embedding
        self.embeddings = HuggingFaceEmbeddings(model_name="keepitreal/vietnamese-sbert")

        # 2. Kết nối tới Vector DB
        if not VECTOR_DB_DIR.exists():
            print(f"⚠️ Cảnh báo: Thư mục {VECTOR_DB_DIR} chưa tồn tại. Hãy chạy ingest_to_vector.py trước!")

        self.vector_db = Chroma(
            persist_directory=str(VECTOR_DB_DIR),
            embedding_function=self.embeddings
        )

        # 3. Prompt chuyên gia — yêu cầu trả lời thuần văn bản, đúng trọng tâm
        template = """Bạn là chuyên gia nông nghiệp lúa gạo tại Việt Nam.
Chỉ dựa vào tài liệu bên dưới để trả lời câu hỏi. Nếu tài liệu không đủ thông tin, hãy trả lời: "Tôi chưa có dữ liệu cụ thể về vấn đề này."

Quy tắc định dạng bắt buộc:
- Viết bằng tiếng Việt, văn xuôi rõ ràng, dễ hiểu.
- TUYỆT ĐỐI KHÔNG dùng ký hiệu Markdown như **, ##, *, _, ` hoặc bất kỳ ký hiệu định dạng đặc biệt nào.
- Nếu câu hỏi liên quan đến bệnh lúa, trình bày lần lượt: 1. Triệu chứng  2. Nguyên nhân  3. Cách xử lý.
- Trả lời ngắn gọn, súc tích và đúng trọng tâm, không lặp lại câu hỏi.

Tài liệu tham khảo:
{context}

Câu hỏi: {question}

Trả lời:"""

        self.prompt = PromptTemplate(template=template, input_variables=["context", "question"])

        # 4. Khởi tạo LLM Groq
        self.llm = ChatGroq(
            temperature=0.1,
            model_name="llama-3.1-8b-instant",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )

    def ask_expert(self, query: str) -> str:
        """Truy vấn RAG và trả về câu trả lời đã được làm sạch ký hiệu."""
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vector_db.as_retriever(search_kwargs={"k": 4}),
            chain_type_kwargs={"prompt": self.prompt}
        )
        result = qa_chain.invoke({"query": query})
        raw_answer = result.get("result", "Không có câu trả lời.")
        return clean_text(raw_answer)

    def reingest_and_reset(self) -> dict:
        """Xóa vector_db cũ, quét lại toàn bộ tài liệu trong data/ và nạp mới tri thức."""
        RAW_DATA_DIR = BASE_DIR / "data" / "raw"
        PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
        VECTOR_DB_DIR = BASE_DIR / "data" / "vector_db"

        # 1. Giải phóng và xóa toàn bộ dữ liệu trong collection hiện tại
        if self.vector_db is not None:
            print("🧹 Đang xóa collection cũ...")
            self.vector_db.delete_collection()
            self.vector_db = None

        # 2. Quét tài liệu từ thư mục raw (PDF, DOCX) và processed (Markdown)
        documents = []

        # PDF/DOCX
        pdf_dir = RAW_DATA_DIR / "pdfs"
        if pdf_dir.exists():
            for file_path in pdf_dir.glob("*.*"):
                if file_path.suffix == ".pdf":
                    loader = PyPDFLoader(str(file_path))
                    documents.extend(loader.load())
                elif file_path.suffix == ".docx":
                    loader = Docx2txtLoader(str(file_path))
                    documents.extend(loader.load())

        # Markdown (Dữ liệu đã crawl)
        md_dir = PROCESSED_DATA_DIR / "markdown"
        if md_dir.exists():
            for file_path in md_dir.glob("*.md"):
                loader = UnstructuredMarkdownLoader(str(file_path))
                documents.extend(loader.load())

        if not documents:
            raise ValueError("Không tìm thấy tài liệu nào (PDF, DOCX, MD) trong thư mục data/ để nạp.")

        # 3. Phân nhỏ văn bản (Chunking)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
        chunks = text_splitter.split_documents(documents)

        # 4. Tạo lại Chroma DB và nạp các vectors mới vào
        self.vector_db = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=str(VECTOR_DB_DIR)
        )

        print(f"✅ Reset & Seed thành công: Nạp {len(documents)} file thành {len(chunks)} vectors.")
        return {
            "status": "success",
            "message": f"Đã reset và seed lại data thành công. Đã nạp {len(documents)} tài liệu thành {len(chunks)} vectors tri thức."
        }


# Khởi tạo instance dùng chung
rag_expert = RAGService()