import os
import time
import hashlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

# Verzeichnis mit Chroma-Datenbank
pdf_folder = "pdf_files"
persist_directory = "chroma_db"

# Das gleiche Embedding-Modell wie zuvor
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def hash_file(file_path):
    """Berechnet den Hash-Wert der Datei, um Duplikate zu vermeiden."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

class PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith(".pdf"):
            return
        
        pdf_path = event.src_path
        print(f"Neue PDF erkannt: {pdf_path}")

        # Chroma-Datenbank laden
        vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embedding_model)

        # PDF verarbeiten
        loader = PyPDFLoader(pdf_path)
        pages = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(pages)
        chunks["metadata"]["index"] = 1 
        vectorstore.add_documents(chunks)
        vectorstore.persist()
        print("------------------------------------chunks----------------------------")
        print(chunks)
        # for doc in documents:
        #     vector = embedding_model.embed(doc)  # Manually embedding each document if necessary
        #     vectorstore.add_document(doc, vector)  # Adding document and its vector to the store

        # vectorstore.persist()  # Ensure all data is saved
        print(f"PDF erfolgreich eingebettet: {pdf_path}")

# Funktion zur Überwachung des PDF-Ordners starten
def start_pdf_monitoring():
    event_handler = PDFHandler()
    observer = Observer()
    observer.schedule(event_handler, pdf_folder, recursive=False)
    observer.start()
    print(f"Überwachung gestartet für: {pdf_folder}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

  
def print_stored_vectors():
    # Chroma-Datenbank laden
    vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embedding_model)
    documents = vectorstore.get()
    print(documents)
    # Überprüfen, ob Dokumente vorhanden sind
    if not documents:
        print("Keine Dokumente in der Datenbank.")
        return
    

# Starte die Überwachung und drucke die gespeicherten Vektoren
start_pdf_monitoring()
print_stored_vectors()



