import requests
import json
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
import os
import re
import time
persist_directory = "chroma_db"


embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embedding_model)

output_dir = 'output_json'


def extract_information_with_model(documents, model_name):
    """ Extrahiert Name, Betreuer und Thema mithilfe des Modells aus den Dokumenten """
    
    if not documents:
        return "Unbekannt", "Unbekannt", "Unbekannt"

    prompt = f"""
    Extrahiere die folgenden Informationen aus dem gegebenen Text und antworte **NUR** mit einem JSON-Objekt:
    
    {{
        "title": "Vollständiger Name oder 'Unbekannt'",
        "betreuer": "Betreuer oder 'Unbekannt'",
        "thema": "Thema oder 'Unbekannt'"
    }}

    Falls eine Information nicht im Text vorkommt, setze sie explizit auf "Unbekannt".  
    Gib **keinen** zusätzlichen Text oder Erklärungen aus – nur das JSON.

    Text:\n{documents}
    """

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}]
    }
    start_time = time.time()
    try:
        response = requests.post("http://localhost:11434/api/chat", json=payload, stream=True)
        response_text = ""
        if response.status_code == 200:
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    json_data = json.loads(line)
                    if "message" in json_data and "content" in json_data["message"]:
                        response_text += json_data["message"]["content"]  
        end_time = time.time()
        elapsed_time = f"{round(end_time - start_time, 2)}s"
        print(response_text)
        return response_text, elapsed_time
                 
    except Exception as e:
        print(f"Fehler bei der Anfrage an das Modell: {e}")
    
    return "Unbekannt"

def extract_json_from_text(text):
    """Extrahiert den JSON-Teil aus dem Text und gibt ihn als Python-Objekt zurück."""
    # Entferne den Markdown-Codeblock (``` ... ```)
    clean_string = re.sub(r"```", "", text)
    
    # Entferne unnötige neue Zeilen und Leerzeichen
    clean_string = clean_string.strip()
    
    match = re.search(r'(\{.*\})', clean_string, re.DOTALL)
    
    if match:
        json_data = match.group(1)
        print(json_data)
        return json_data
    else:
        print("Kein JSON im Text gefunden!")
        return None

def clean_filename(filename):
    """Bereinigt den Dateinamen von ungültigen Zeichen für das Dateisystem."""
    return re.sub(r'[\\/*?:"<>|]', '_', filename)

def save_model_response_to_json(response_data,elapsed_time, model_folder):
    """Speichert die extrahierten Informationen in einer JSON-Datei."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    cleaned_response = extract_json_from_text(response_data)
    
    try:
        json_data = json.loads(cleaned_response)

        json_data["Antwortzeit"] = elapsed_time

        filename = clean_filename(f"{json_data['title']}_output.json")
        json_filename = os.path.join(output_dir, model_folder, filename)

        # Sicherstellen, dass der Modell-Ordner existiert
        if not os.path.exists(os.path.join(output_dir, model_folder)):
            os.makedirs(os.path.join(output_dir, model_folder))

        # Speichern der Antwort in einer JSON-Datei
        with open(json_filename, 'w', encoding="utf-8") as json_file:
            json.dump(json_data, json_file, indent=4, ensure_ascii=False)

        print(f"Extrahierte Informationen gespeichert in {json_filename}")
    
    except json.JSONDecodeError as e:
        print(f"Fehler beim Parsen des JSON: {e}")


Documents = vectorstore.get()["documents"]

# Llama
response_data_model_1, elapsed_time_model1 = extract_information_with_model(Documents, "llama3.1:8b")
save_model_response_to_json(response_data_model_1,elapsed_time_model1, model_folder="Llama")

#DeepSeek
response_data_model_2,elapsed_time_model2 = extract_information_with_model(Documents, "deepseek-r1:14b")
save_model_response_to_json(response_data_model_2, elapsed_time_model2, model_folder="DeepSeek")

print(f"Extrahierte Informationen für beide Modelle gespeichert.")