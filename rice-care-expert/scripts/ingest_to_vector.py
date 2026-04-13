import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredMarkdownLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Định nghĩa đường dẫn theo cấu trúc project của bạn
BASE_DIR = Path(__file__).resolve().parent.parent
DOTENV_PATH = BASE_DIR / ".env"
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"  # Thêm đường dẫn tới dữ liệu đã xử lý
VECTOR_DB_DIR = BASE_DIR / "data" / "vector_db"  # Lưu vào data/vector_db theo cấu trúc bạn gửi

load_dotenv(DOTENV_PATH)


def ingest_data():
    documents = []

    print("🚀 Bắt đầu quá trình nạp tri thức vào hệ thống...")

    # --- 1. Quét tài liệu thô (PDF và DOCX) ---
    pdf_dir = RAW_DATA_DIR / "pdfs"
    if pdf_dir.exists():
        print(f"📄 Đang quét file PDF/DOCX tại: {pdf_dir}")
        for file_path in pdf_dir.glob("*.*"):
            if file_path.suffix == ".pdf":
                loader = PyPDFLoader(str(file_path))
                documents.extend(loader.load())
            elif file_path.suffix == ".docx":
                loader = Docx2txtLoader(str(file_path))
                documents.extend(loader.load())

    # --- 2. QUÉT FILE MARKDOWN (Dữ liệu đã crawl) ---
    md_dir = PROCESSED_DATA_DIR / "markdown"
    if md_dir.exists():
        print(f"📝 Đang quét file Markdown (dữ liệu crawl) tại: {md_dir}")
        for file_path in md_dir.glob("*.md"):
            # Sử dụng UnstructuredMarkdownLoader để giữ cấu trúc tốt hơn
            loader = UnstructuredMarkdownLoader(str(file_path))
            documents.extend(loader.load())

    if not documents:
        print("⚠️ Không tìm thấy tài liệu nào (PDF, DOCX, MD). Hãy kiểm tra lại các thư mục data/")
        return

    # 3. Chia nhỏ văn bản (Chunking)
    # Với Markdown, chunk_size nên vừa phải để giữ nguyên ngữ cảnh của từng mục bệnh
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    chunks = text_splitter.split_documents(documents)

    # 4. Sử dụng mô hình Embedding miễn phí (Vietnamese SBERT)
    print(f"🧠 Đang mã hóa {len(chunks)} đoạn văn bản (Mô hình: vietnamese-sbert)...")

    model_name = "keepitreal/vietnamese-sbert"
    # Thêm thiết bị xử lý (cuda nếu có GPU, không thì cpu)
    model_kwargs = {'device': 'cpu'}
    encode_kwargs = {'normalize_embeddings': False}

    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )

    # 5. Lưu vào Vector Database
    # Xóa database cũ nếu bạn muốn nạp mới hoàn toàn (tùy chọn)
    # if VECTOR_DB_DIR.exists():
    #     import shutil
    #     shutil.rmtree(VECTOR_DB_DIR)

    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(VECTOR_DB_DIR)
    )

    print(f"✅ THÀNH CÔNG! {len(documents)} file đã được chuyển đổi thành {len(chunks)} vector tri thức.")
    print(f"📍 Database lưu tại: {VECTOR_DB_DIR}")


if __name__ == "__main__":
    ingest_data()