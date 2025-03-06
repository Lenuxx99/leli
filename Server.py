from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from werkzeug.utils import secure_filename
import requests
import json
import os 
import time
from extract_info_llm import save_model_response_to_json_output, extract_information_with_model

# Flask-App erstellen
app = Flask(__name__, static_folder='./frontend/dist', static_url_path=None)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}})
socketio = SocketIO(app, cors_allowed_origins= ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5000"] ,engineio_logger=True)  # In der Entwicklungsumgebung (React auf Port 5173), handelt es sich um Cross-Origin-Anfragen. Deshalb muss das Flask-Backend CORS erlauben

persist_directory = "chroma_db"

# Das gleiche Embedding-Modell wie bei der Erstellung verwenden
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Chroma-Datenbank laden
vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embedding_model)

# Ordner für Uploads erstellen
UPLOAD_FOLDER = os.path.join("uploads")  # os.getcwd() gibt das aktuelle Arbeitsverzeichnis (Current Working Directory, CWD) zurück.
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    full_path = os.path.join(app.static_folder, path)

    # Debug: Pfad ausgeben
    print(f"Requested path: {path}")
    print(f"Full static path: {full_path}")

    if path != "" and os.path.exists(full_path):
        print(f"File found. Serving: {full_path}")
        return send_from_directory(app.static_folder, path)

    # Fallback: Datei direkt auslesen und zurückgeben
    print("File not found. Serving index.html")
    with open(os.path.join(app.static_folder, 'index.html')) as file:
        return file.read(), 200, {'Content-Type': 'text/html'}

documents = []  # Liste für Dokumente
already_processed = set() 
file_urls = []

# Situation	                            Verwendet
# Datei-Upload (PDF, Bild)	            request.files
# JSON-Daten (z. B. Text, Arrays)	    request.json
# Formulardaten (x-www-form-urlencoded)	request.form
@app.route("/api/embedding", methods=["POST"])
def handle_embedding():
    if "AllPdfs" not in request.files:
        return jsonify({"error": "Keine Datei hochgeladen"}), 400
    
    file_urls.clear()

    files = request.files.getlist("AllPdfs")
    # filenames = [file.filename for file in files]
    
    for file in files:
        # tnaa7i espace w sonderzeichen
        filename = secure_filename(file.filename)

        file_urls.append({"name": file.filename, "url": f"http://localhost:5000/uploads/{filename}"})

        if filename in already_processed:
            print(f"Datei {filename} wurde bereits verarbeitet.")
            continue  # Überspringe bereits verarbeitete Dateien
        
        already_processed.add(filename)

        # Datei temporär speichern
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # PDF laden & in Chunks aufteilen
        loader = PyPDFLoader(filepath)
        pages = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(pages)

        print(f"Anzahl der Chunks: {len(chunks)}")

        global documents
        documents.extend(chunks)

    # Chroma-Datenbank aktualisieren
    if documents:
        print("Aktualisiere Chroma-Datenbank...")
        vectorstore.add_documents(documents)
        vectorstore.persist()
        print("ChromaDB gespeicherte Daten------------------------------------")
        print(vectorstore.get())
        print("---------------------------------------------------------------")
        documents.clear()  

    return jsonify({"files": file_urls}), 200

@app.route("/api/delete_embedding", methods=["POST"])
def handle_delete_embedding():
    try:
        data = request.get_json()  # { filename: fileToDelete.name }
        filename_ = data.get("filename")

        # file_urls.append({...})	❌	    append() verändert nur den Inhalt der globalen Liste.
        # file_urls = []	        ✅	    Hier wird die ganze Variable überschrieben, nicht nur der Inhalt.
        # file_urls += [...]	    ✅	    += erzeugt intern eine neue Liste, daher braucht es global.
        # global file_urls
        # file_urls = [file for file in file_urls if file["name"] != filename_]

        filename = secure_filename(filename_)

        if not filename:
            return jsonify({"error": "Kein Dateiname angegeben"}), 400
        
        # 1️⃣ **Embeddings aus ChromaDB entfernen**
        vectorstore.delete(where={"source": os.path.join(UPLOAD_FOLDER, filename)})
        vectorstore.persist()

        print("Aktualisiere Chroma-Datenbank nachdem Löschen...")
        print("ChromaDB gespeicherte Daten------------------------------------")
        print(vectorstore.get())
        print("---------------------------------------------------------------")

        if filename in already_processed:
            already_processed.remove(filename)

        # 2️⃣ **Datei aus dem Upload-Ordner entfernen**
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({"message": f"Datei {filename} und zugehörige Embeddings gelöscht"}), 200
        else:
            return jsonify({"error": "Datei nicht gefunden"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/getjson", methods=["POST"])
def getJson():
    try:
        data = request.get_json() 
        model = data["model"]
        Documents = vectorstore.get()["documents"]
        print("Genutztes Model für die Daten extraktion-------------------------------------------------------------")
        print(model)

        # Prüft, wie viele Dateien untersucht werden
        unique_sources = set(meta["source"] for meta in vectorstore.get()["metadatas"])
        num_sources = len(unique_sources)

        if num_sources == 0:
            return jsonify({"message":"no pdf ist hochgeladen"}), 400
        
        response = {"message": "Modell nicht unterstützt"}  

        if model == "Lama3.1":
            # Llama
            response_data_model_1, elapsed_time_model1 = extract_information_with_model(Documents, "llama3.1:8b", num_sources)
            response = save_model_response_to_json_output(response_data_model_1,elapsed_time_model1, num_sources)
        elif model == "DeepSeek" : 
            #DeepSeek
            response_data_model_2,elapsed_time_model2 = extract_information_with_model(Documents, "deepseek-r1:14b", num_sources)
            response = save_model_response_to_json_output(response_data_model_2, elapsed_time_model2, num_sources)
        
        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
def call (user_input, model, source):
    try:
        # Ähnlichkeitssuche in der Chroma-Datenbank durchführen
        filter_criteria = {"source": source} if source else None
        similar_docs = vectorstore.similarity_search(user_input, k=3, filter=filter_criteria)

        context = ""
        if (source):
            # Kontext aus den Dokumenten extrahieren
            context = "\n".join([doc.page_content for doc in similar_docs])

        print("Extrahierte kontext----------------------------------")
        print(context)
        print("-----------------------------------------------------")

        full_prompt = f"""
            Bitte beantworte die folgende Frage präzise und detailliert, basierend auf den bereitgestellten Informationen.
            Verwende die folgenden Hintergrundinformationen und beziehe dich direkt auf diese, ohne zu erwähnen, dass die Information extern stammt.
            Die bereitgestellten Informationen dienen als Grundlage für deine Antwort.

            Informationen:\n{context if context else 'Es wurden keine relevanten Informationen gefunden. Bitte wählen Sie ein PDF-Dokument aus, damit wir Ihnen weiterhelfen können.'}\n\n

            Frage: {user_input}

            Falls es keine Kontext gibt, erwähne bitte, dass der Benutzer ein PDF auswählen muss, um weitere Unterstützung zu erhalten.
            Die Antwort sollte klar strukturiert, ausführlich und direkt auf die gestellte Frage bezogen sein.
        """

        model_config = {
            "Lama3.1": {
                "model": "llama3.1:8b"
            },
            "DeepSeek": {
                "model": "deepseek-r1:14b"
            },
            "GPT": {
                "model": "gpt-3.5-turbo"
            }
        }

        if model in model_config:
            payload = {
                "model": model_config[model]["model"],
                "messages": [{"role": "user", "content": full_prompt}]
            }
        # else:
        #     payload = {
        #         "model": "llama3.1:8b",
        #         "messages": [{"role": "user", "content": full_prompt}]
        #     }

        url = "http://localhost:11434/api/chat"

        response = requests.post(url, json=payload, stream=True, timeout=15)

        if response.status_code == 200:
            first_response = True
            start_time = None

            for line in response.iter_lines(decode_unicode=True):
                if line:
                    json_data = json.loads(line)

                    if "message" in json_data and "content" in json_data["message"]:
                        if first_response:
                            start_time = time.time()  # Timer starten, wenn erste Antwort kommt
                            first_response = False  # Timeout ab jetzt nicht mehr relevant
                        
                        token = json_data["message"]["content"]
                        emit('response', {'response': token})
            
            if start_time:  # Falls eine Antwort kam, berechne die Antwortzeit
                elapsed_time = round(time.time() - start_time, 2)
                print(f"Antwortzeit: {elapsed_time}s")
                emit('response_time', {'time': elapsed_time})
        else:
            emit('error', {'error': 'Fehler beim Verbinden mit dem Modell'})

    except requests.exceptions.Timeout:
        print("⚠️ Timeout! Der Server hat zu lange gebraucht, um zu starten.")
        emit('timeout', {
            'message': 'Der Server hat nicht innerhalb von 15 Sekunden geantwortet. ',
            'retry_possible': True
        })

@socketio.on('message')
def handle_message(data):
    user_input = data['text']
    model = data["model"]
    print(model)
    file_path = data.get("file", "")
    if(file_path) :
        file_path = os.path.join(UPLOAD_FOLDER, file_path)
    call(user_input, model, file_path)

@socketio.on('continue_request')
def continue_request(data):
    user_input = data['text']
    model = data["model"]
    file_path = data.get("file", "")
    if(file_path) :
        file_path = os.path.join(UPLOAD_FOLDER, file_path)
    call(user_input, model, file_path)

if __name__ == '__main__':
    socketio.run(app, debug=True)  # Flask standardmäßig Port 5000 oder socketio.run(app, debug=True, port = 8000) 







# @socketio.on('event_one')
# def handle_event_one(data):
#     print("Data for event_one:", data)

# @socketio.on('event_two')
# def handle_event_two(data):
#     print("Data for event_two:", data)