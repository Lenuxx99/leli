import time
import os
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

path = "pdf_files"
chroma = "chroma_db"
embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma(persist_directory=chroma, embedding_function=embedding)

already_processed = set()

if not os.path.exists(path):
    os.makedirs(path)
    print(f"Ordner /'{path}' wurde erstellt.")

documents = []
try:
    while True:
        print("Suche nach Änderungen...")
        
        # Schleife über vorhandene Dateien
        for pdf_file in os.listdir(path):
            if pdf_file.endswith(".pdf"):
                pdf_path = os.path.join(path, pdf_file)
                
                # Prüfen, ob diese Datei neu ist
                if pdf_path not in already_processed:
                    print(f"Verarbeite neue Datei: {pdf_path}")
                    
                    loader = PyPDFLoader(pdf_path)
                    pages = loader.load()
                    
                    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                    chunks = text_splitter.split_documents(pages)
                    # chunk ist ein Document-Objekt mit den Attributen: chunk.page_content (Textinhalt) // chunk.metadata (eine Dictionary mit Metadaten) 
                    # chunk in LangChain in der Regel ein Objekt vom Typ Document ist und kein verschachteltes Dictionary, chunk["metadata"]["id"] ist nicht erlaubt
                    # for chunk in chunks:                    
                    #     chunk.metadata["id"]= 1
                    #     print(chunk)
                    documents.extend(chunks)
                    already_processed.add(pdf_path)
        
        # Wenn neue Dokumente gefunden wurden, Chroma aktualisieren
        if documents:
            print("Aktualisiere Chroma-Datenbank...")
            vectorstore.add_documents(documents)
            vectorstore.persist()
            
            # Leere die Liste, damit nur **neue** Chunks beim nächsten Durchgang hinzukommen
            documents = []
            print(vectorstore.get())
        
        current_pdfs_on_disk = set()
        for pdf_file in os.listdir(path):
            if pdf_file.endswith(".pdf"):
                pdf_path = os.path.join(path, pdf_file)
                current_pdfs_on_disk.add(pdf_path)

        deleted_pdfs = already_processed - current_pdfs_on_disk
        if deleted_pdfs:
            print("Folgende Dateien gelten als gelöscht und werden aus der Datenbank entfernt:")
            for deleted_file in deleted_pdfs:
                print(deleted_file)

            # Für jede gelöschte Datei die Einträge in Chroma löschen
            for deleted_file in deleted_pdfs:
                # Hier löschen wir nach dem Metadatum "source", 
                # das beim Erstellen der Chunks als PDF-Pfad gesetzt wurde
                vectorstore.delete(where={"source": deleted_file})

                # Optional: Aus dem Set entfernen, damit wir es nicht nochmal löschen
                already_processed.remove(deleted_file)

            vectorstore.persist()
            print(vectorstore.get())
        else:
            print("Keine gelöschten PDF-Dateien gefunden.")
        print("Keine neuen PDFs gefunden. Warte 10 Sekunden...")
        time.sleep(10) 
except KeyboardInterrupt:
    print("Skript wird beendet...")