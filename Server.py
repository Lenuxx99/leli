from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
import requests
import json
import os 
import time

# Flask-App erstellen
app = Flask(__name__, static_folder='./chatbot-frontend/build', static_url_path=None)
build_folder = os.path.abspath('./chatbot-frontend/build')
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5000", "http://127.0.0.1:5000"], engineio_logger=True)  # In der Entwicklungsumgebung (wenn React auf Port 3000 und Flask auf Port 5000 läuft), handelt es sich um Cross-Origin-Anfragen. Deshalb muss das Flask-Backend CORS erlauben (unsicher)

persist_directory = "chroma_db"

# Das gleiche Embedding-Modell wie bei der Erstellung verwenden
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Chroma-Datenbank laden
vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embedding_model)

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

@app.route('/api/login', methods=['POST'])
def login_api():
    data = request.get_json()  
    username = data.get('username')
    password = data.get('password')
    
    
    # Beispiel: Nur eine Demo-Antwort
    if username == "demo" and password == "secret":
        return jsonify({"status": "ok", "message": "Login erfolgreich"})
    else:
        return jsonify({"status": "error", "message": "Falsche Daten!"}), 401


@socketio.on('message')
def handle_message(data):
    try:
        user_input = data['text']
        model = data["model"]
        
        # Ähnlichkeitssuche in der Chroma-Datenbank durchführen
        similar_docs = vectorstore.similarity_search(user_input, k=3)

        print(vectorstore.get()["documents"])

        # Kontext aus den Dokumenten extrahieren
        context = "\n".join([doc.page_content for doc in similar_docs])

        full_prompt = f"""
            Bitte beantworte die folgende Frage präzise und detailliert, basierend auf den bereitgestellten Informationen.
            Verwende die folgenden Hintergrundinformationen und beziehe dich direkt auf diese, ohne zu erwähnen, dass die Information extern stammt.
            Die bereitgestellten Informationen dienen als Grundlage für deine Antwort.
            
            Informationen:\n{context}\n\n

            Frage: {user_input}

            Falls die Frage zu allgemein ist oder keine echte Frage gestellt wurde, antworte allgemein und vermeide es, detaillierte Informationen zu liefern.
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
        else:
            payload = {
                "model": "llama3.1:8b",
                "messages": [{"role": "user", "content": full_prompt}]
            }
        
        start_time = time.time()

        url = "http://localhost:11434/api/chat"

        response = requests.post(url, json=payload, stream=True)
        if response.status_code == 200:
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    json_data = json.loads(line)
                    if "message" in json_data and "content" in json_data["message"]:
                        # print(json_data["message"]["content"])
                        emit('response', {'response': (json_data["message"]["content"])})
            
            end_time = time.time()
            elapsed_time = round(end_time - start_time, 2)  # Zeit in Sekunden
            print(f"time to needed to answer : {elapsed_time}s")
            emit('response_time', {'time': elapsed_time})
        else:
            emit('error', {'error': 'Failed to connect to the chat model'})
    except Exception as e:
        app.logger.error(f'Error processing request: {str(e)}')
        emit('error', {'error': 'Internal Server Error'})

if __name__ == '__main__':
    socketio.run(app, debug=True)  # Flask standardmäßig Port 5000 oder socketio.run(app, debug=True, port = 8000) 







# @socketio.on('event_one')
# def handle_event_one(data):
#     print("Data for event_one:", data)

# @socketio.on('event_two')
# def handle_event_two(data):
#     print("Data for event_two:", data)