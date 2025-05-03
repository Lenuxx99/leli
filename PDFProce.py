import os
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

class PDFProcessor:
    def __init__(self, upload_folder: str):
        self.upload_folder = upload_folder

    def save_file(self, file, filename: str) -> str:
        filepath = os.path.join(self.upload_folder, filename)
        file.save(filepath)
        return filepath

    def extract_text_chunks(self, filepath: str, chunk_size=200, chunk_overlap=50):
        loader = PyPDFLoader(filepath)
        pages = loader.load()  

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        chunks = text_splitter.split_documents(pages)
        if not chunks:
            return None

        return chunks