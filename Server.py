from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from werkzeug.utils import secure_filename
import requests
import json
import os 
import time
from extract_info_llm import save_model_response_to_json_output, extract_information_with_model
from test_models import query_model, evaluate_response
import logging
import sys
import psutil 
import platform
import asyncio
from collections import OrderedDict

# Flask-App erstellen
app = Flask(__name__, static_folder='./frontend/dist', static_url_path=None)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}})
socketio = SocketIO(app, cors_allowed_origins= ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5000"] )#,engineio_logger=True  # In der Entwicklungsumgebung (React auf Port 5173), handelt es sich um Cross-Origin-Anfragen. Deshalb muss das Flask-Backend CORS erlauben

# Konfiguriere das Logging
logging.basicConfig(
    level=logging.INFO,  # Stellt sicher, dass alle Logs ab INFO-Niveau erfasst werden
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),  # Ausgabe auf der Konsole
        logging.FileHandler("app.log")      # Log-Datei zum Speichern der Logs
    ]
)
# Setze den werkzeug-Logger, um sowohl INFO- als auch ERROR-Logs anzuzeigen
log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO)  # Zeigt sowohl INFO- als auch ERROR-Logs an

persist_directory = "chroma_db"

# Embedding-Modell
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Chroma-Datenbank laden
vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embedding_model, collection_name="vectorstore") # , collection_metadata={"hnsw:space": "cosine"}

# Ordner für Uploads erstellen
UPLOAD_FOLDER = os.path.join("uploads") 
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

logging.info("Server gestartet")
logging.info(f"CPU-Modell: {platform.processor()}")
logging.info(f"Aktuelle CPU-Auslastung:{psutil.cpu_percent(interval=1)}%")

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

    logging.info(f"Frontend-Anfrage: {path} (Serving index.html)")

    # Fallback: Datei direkt auslesen und zurückgeben
    print("File not found. Serving index.html")
    with open(os.path.join(app.static_folder, 'index.html')) as file:
        return file.read(), 200, {'Content-Type': 'text/html'}

documents = [] 
already_processed = set() 
file_urls = []

# Situation	                            Verwendet
# Datei-Upload (PDF, Bild)	            request.files
# JSON-Daten (z. B. Text, Arrays)	    request.json
# Formulardaten (x-www-form-urlencoded)	request.form
@app.route("/api/embedding", methods=["POST"])
def handle_embedding():
    if "AllPdfs" not in request.files:
        logging.warning("Keine Datei hochgeladen")
        return jsonify({"error": "Keine Datei hochgeladen"}), 400
    
    file_urls.clear()

    files = request.files.getlist("AllPdfs")
    # filenames = [file.filename for file in files]
    
    for file in files:
        # tnaa7i espace w sonderzeichen
        filename = secure_filename(file.filename)

        file_urls.append({"name": file.filename, "url": f"http://localhost:5000/uploads/{filename}"})

        # files sind bereits in Frontend gefiltert
        if filename in already_processed:
            logging.info(f"Datei {filename} wurde bereits verarbeitet, wird übersprungen.")
            continue  # Überspringe bereits verarbeitete Dateien
        
        already_processed.add(filename)

        # Datei temporär speichern
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)

        # PDF laden & in Chunks aufteilen
        loader = PyPDFLoader(filepath)
        pages = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)  # Jeder einzelne Chunk hat maximal 800 Zeichen
        chunks = text_splitter.split_documents(pages)

        logging.info(f"Datei {filename} eingefuegt, {len(chunks)} Chunks extrahiert.")

        global documents
        documents.extend(chunks)

    # Chroma-Datenbank aktualisieren
    if documents:
        logging.info("Aktualisiere Chroma-Datenbank...")
        vectorstore.add_documents(documents)
        vectorstore.persist()
        logging.info("Chroma-Datenbank aktualisiert.")
        logging.info("ChromaDB gespeicherte Daten:")
        logging.info(vectorstore.get())
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
            logging.warning("Kein Dateiname angegeben.")
            return jsonify({"error": "Kein Dateiname angegeben"}), 400
        
        # Embeddings aus ChromaDB entfernen
        vectorstore.delete(where={"source": os.path.join(UPLOAD_FOLDER, filename)})
        vectorstore.persist()

        logging.info(f"Embeddings fuer {filename} geloescht.")
        logging.info(f"Chroma-Datenbank aktualisiert.")

        logging.info("ChromaDB gespeicherte Daten:")
        logging.info(vectorstore.get())


        if filename in already_processed:
            already_processed.remove(filename)

        # Datei aus dem Upload-Ordner entfernen
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        if os.path.exists(filepath):
            os.remove(filepath)
            logging.info(f"Datei {filename} erfolgreich geloescht.")
            return jsonify({"message": f"Datei {filename} und zugehörige Embeddings gelöscht"}), 200
        else:
            return jsonify({"error": "Datei nicht gefunden"}), 404

    except Exception as e:
        logging.error(f"Fehler beim Löschen: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/getjson", methods=["POST"])
def getJson():
    try:
        data = request.get_json() 
        model = data["model"]

        logging.info("Button 'Extract all Infos' zum Erstellen der JSON-Datei angeklickt")
        
        # Prüft, wie viele Dateien untersucht werden
        unique_sources = set(meta["source"] for meta in vectorstore.get()["metadatas"])
        num_sources = len(unique_sources)

        if num_sources == 0:
            return jsonify({"message":"no pdf ist hochgeladen"}), 400
        

        num_vectors = vectorstore._collection.count()
        logging.info(f"Anzahl der Vektoren in ChromaDB: {num_vectors}")
        
        query = "Anmeldung zur Bachelorarbeit Student Thema der Bachelorarbeit Betreuer Matrikelnummer"

        # Führe die Ähnlichkeitssuche mit Score durch
        retrieved_texts = vectorstore.similarity_search_with_score(query, k = num_vectors)

        logging.info("Aehnlichkeit Score jeder Vektor:")
        for doc, score in retrieved_texts:
            cleaned_text = doc.page_content[:100].replace("\n", " ")
            logging.info(f"Score: {score} / Vektor_text: {cleaned_text}")
                    
        print(vectorstore._collection._client.get_collection(name="vectorstore"))
    
        # Die euklidische Distanz l2 misst den geradlinigen Abstand zwischen zwei Punkten im Raum. 
        # Sie berücksichtigt sowohl die Richtung als auch die Länge der Vektoren. Je kleiner der Wert, desto ähnlicher sind die Punkte.
        threshold = 1.2
        
        retrieved_texts = [doc.page_content for doc, score in retrieved_texts if score <= threshold]
        
        logging.info(f"Genutztes Model: {model}")
        logging.info(f"Anzahl der zu bearbeitenden Dateien: {num_sources}")
        # print("Relevante Informationen gefunden:")
        # for text in retrieved_texts:
        #    print(text)
        logging.info("JSON file wird erstellt....")
        
        response = {"message": "Modell nicht unterstützt"}  
        
        if model == "Lama3.1":
            # Llama
            response_data_model_1, elapsed_time_model1 = extract_information_with_model(retrieved_texts, "llama3.1:8b", num_sources)
            response = save_model_response_to_json_output(response_data_model_1, elapsed_time_model1, num_sources)
        elif model == "DeepSeek" : 
            #DeepSeek
            response_data_model_2,elapsed_time_model2 = extract_information_with_model(retrieved_texts, "deepseek-r1:14b", num_sources)
            response = save_model_response_to_json_output(response_data_model_2, elapsed_time_model2, num_sources)
        elif model == "Mistral" :
            response_data_model_2,elapsed_time_model2 = extract_information_with_model(retrieved_texts, "mistral", num_sources)
            response = save_model_response_to_json_output(response_data_model_2, elapsed_time_model2, num_sources)

        logging.info("JSON file erfolgreich erstellt")

        return jsonify(response), 200
    except Exception as e:
        logging.info(f"Erstellung des JSON Files fehlgeschlagen:{str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/testmodel", methods = ["POST"])
def testmodels():
    models = [
        "llama3.1:8b",
        "deepseek-r1:8b",
        "mistral"
    ]

    # Testfragen (Kriterien für die CSV-Spalten)
    questions = [
        ("Thema?", "Die Antwort muss das Thema der Bachelorarbeit erwähnen."),
        ("Betreuer Name?", "Die Antwort muss den Namen des Betreuers enthalten."),
        ("Supervisor name?", "The answer must include the supervisor's name."),
        ("E-Mail vom Betreuer?", "Die Antwort muss die E-Mail des Betreuers nennen."),
    ]
    data = request.get_json()

    file_path = os.path.join(UPLOAD_FOLDER, data["file"])
    results = []
    response_infos = []
    
    for model_name in models:
        row = [model_name]  # Erste Spalte: Modellname
        for question, Erwartete_Inhalte in questions:
            logging.info(f"[{model_name}] '{question}'")
            filter_criteria = {"source": file_path} 
            similar_docs = vectorstore.similarity_search(question, k=3, filter=filter_criteria)            
            context = "\n".join([doc.page_content for doc in similar_docs])

            times, response , hardware = asyncio.run(query_model(model_name, question, context))
            bewertung  = evaluate_response (response, Erwartete_Inhalte, context, question)
            response_infos.append(OrderedDict([
                    ("Model", model_name),
                    ("Frage", question),
                    ("Response", response),
                    ("Antwortzeit", times),
                    ("Antwort Bewertung", bewertung),
                    ("Hardware Auslastung", hardware)
                ]))
            row.append(times)  # Zeiten in die Zeile einfügen
        results.append(row)  # results = [[model_name1, times_question1, times_question2, times_question3], [model_name2, times_question1, times_question2, times_question3]...]
    logging.info(results)
    return jsonify({"results": results, "questions": questions, "allInfos": response_infos}), 200

def call (user_input, model, source):
    try:
        # Ähnlichkeitssuche in der Chroma-Datenbank durchführen mit Filter
        filter_criteria = {"source": source} if source else None
        similar_docs = vectorstore.similarity_search_with_score(user_input, k=3, filter=filter_criteria)

        context = ""
        if (source):
            num_vectors = vectorstore._collection.get(where={"source": source})
            logging.info(f"Anzahl der gespeicherten Vektoren fuer {source}: {len(num_vectors['ids'])}")
            logging.info(f"Die {min(3, len(similar_docs))} aehnlichsten Vektoren mit Score (falls verfuegbar):")
            for doc, score in similar_docs:
                cleaned_text = doc.page_content[:100].replace("\n", " ")
                logging.info(f"Score: {score} / Vektor_text : {cleaned_text}")
            
            threshold = 1.5
            # Kontext aus den Dokumenten extrahieren
            context = "\n".join([doc.page_content for doc, score in similar_docs if score <= threshold ])
            if(context == ""):
                context = "Keine relevante Informationen gefunden" 
                logging.info(context)  
            else:
                cleaned_context = context[:1000].replace('\n', ' ')
                logging.info(f"Extrahierter Kontext nach Filterung mit einem Threshold von 1.5: {cleaned_context}...")   
        else :
            context = "Es wurden keine relevanten Informationen gefunden. Bitte waehlen Sie ein PDF-Dokument aus, damit wir Ihnen weiterhelfen koennen."
            logging.info(context) 

        full_prompt = f"""
            Bitte beantworte die folgende Frage präzise und detailliert anhand der bereitgestellten Informationen.  
            Nutze ausschließlich die unten angegebenen Hintergrundinformationen und integriere sie direkt in deine Antwort, ohne explizit auf eine externe Quelle hinzuweisen.  

            Falls die bereitgestellten Informationen keine relevante Antwort auf die Frage enthalten, informiere den Benutzer darüber, dass die ausgewählte PDF keine relevanten Informationen enthält.  

            Falls kein Kontext vorhanden ist, weise den Benutzer darauf hin, dass er zunächst eine PDF-Datei auswählen muss, um eine fundierte Antwort zu erhalten.  

            Falls der Benutzer keine spezifische Frage stellt, antworte normal, ohne die Hintergrundinformationen zu berücksichtigen.  

            Formuliere deine Antwort logisch, präzise und verständlich, ohne vom Thema abzuschweifen.  

            **Hintergrundinformationen:**  
            {context}  

            **Benutzerfrage:**  
            {user_input}  
            """

        model_config = {
            "Lama3.1": {
                "model": "llama3.1:8b"
            },
            "DeepSeek": {
                "model": "deepseek-r1:8b"
            },
            "Mistral": {
                "model": "mistral"
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

        cpu_before = psutil.cpu_percent(interval=None)
        ram_before = psutil.virtual_memory().percent
        logging.info(f"Vor der Anfrage - CPU: {cpu_before}%, RAM: {ram_before}%")

        response = requests.post(url, json=payload, stream=True, timeout=20)

        if response.status_code == 200:
            first_response = True
            start_time = None

            logging.info(f"{model} Antwort:")

            # **2. Während der Verarbeitung - CPU & RAM messen**
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    json_data = json.loads(line)

                    if "message" in json_data and "content" in json_data["message"]:
                        if first_response:
                            start_time = time.time()  # Timer starten, wenn erste Antwort kommt
                            first_response = False  # Timeout ab jetzt nicht mehr relevant

                        # CPU & RAM während der Verarbeitung
                        cpu_during = psutil.cpu_percent(interval=None)
                        ram_during = psutil.virtual_memory().percent
                        logging.info(f"Waehrend der Antwort - CPU: {cpu_during}%, RAM: {ram_during}%")

                        token = json_data["message"]["content"]
                        logging.info(json_data)
                        emit('response', {'response': token})

            # **3. CPU- & RAM-Auslastung NACH der Antwort**
            if start_time:
                elapsed_time = round(time.time() - start_time, 2)
                emit('response_time', {'time': elapsed_time, "model": model})
                logging.info(f"Antwortzeit: {elapsed_time}s")

            cpu_after = psutil.cpu_percent(interval=None)
            ram_after = psutil.virtual_memory().percent
            logging.info(f"Nach der Anfrage - CPU: {cpu_after}%, RAM: {ram_after}%")
        else:
            emit('error', {'error': 'Fehler beim Verbinden mit dem Modell. Aktualisiere die Seite und wähle ein anderes Modell aus.'})

    except requests.exceptions.Timeout as e:
        logging.error(f"Anfragefehler (Timeout): {str(e)}")
        print("⚠️ Timeout! Der Server hat zu lange gebraucht, um zu starten.")
        emit('timeout', {
            'message': 'Der Server hat nicht innerhalb von 15 Sekunden geantwortet. ',
            'retry_possible': True
        })

@socketio.on('message')
def handle_message(data):
    user_input = data['text']
    model = data["model"]
    file_path = data.get("file", "")
    if(file_path) :
        file_path = os.path.join(UPLOAD_FOLDER, file_path)

    logging.info(f"Neue Anfrage - Model: {model}, Datei: {file_path if file_path else 'Keine'}")
    logging.info(f"Prompt: {user_input}")
    call(user_input, model, file_path)

@socketio.on('continue_request')
def continue_request(data):
    user_input = data['text']
    model = data["model"]
    file_path = data.get("file", "")
    if(file_path) :
        file_path = os.path.join(UPLOAD_FOLDER, file_path)

    logging.info(f"Fortgesetzte Anfrage - Model: {model}, Datei: {file_path if file_path else 'Keine'}")
    call(user_input, model, file_path)

if __name__ == '__main__':
    # Startet die Flask-Anwendung mit SocketIO
    # `threaded=True` ermöglicht die gleichzeitige Bearbeitung mehrerer Anfragen (Multithreading) und eventloop nicht blockieren
    # Standardmäßig ist `threaded=True` bereits aktiv, daher kann es auch weggelassen werden.
    # Alternativ kann `port=5000` explizit angegeben werden, falls ein anderer Port gewünscht ist.
    # Gunicorn 
    socketio.run(app, debug=False)  # Startet Flask auf dem Standardport 5000






# @socketio.on('event_one')
# def handle_event_one(data):
#     print("Data for event_one:", data)

# @socketio.on('event_two')
# def handle_event_two(data):
#     print("Data for event_two:", data)