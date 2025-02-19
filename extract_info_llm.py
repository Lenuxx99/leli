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


def extract_information_with_model(documents, model_name, num_source):
    """ Extrahiert Name, Betreuer und Thema mithilfe des Modells aus den Dokumenten """
    
    if not documents:
        return "Unbekannt", "Unbekannt", "Unbekannt"

    prompt = f"""
        Extrahiere die folgenden Informationen aus dem gegebenen Text und antworte **NUR** mit einem oder mehreren JSON-Objekten:
        
        **Format für eine einzelne Quelle:**
        Falls es nur ein einziges Thema gibt, antworte mit einem **einzelnen JSON-Objekt** im folgenden Format:
        {{
            "title": "Vollständiger Name oder 'Unbekannt'",
            "betreuer": "Betreuer oder 'Unbekannt'",
            "thema": "Thema oder 'Unbekannt'"
        }}

        **Format für mehrere Quellen:**
        Falls der Text **mehrere verschiedene Themen** enthält, erstelle für **jedes Thema ein separates JSON-Objekt** und gib eine **Liste von JSON-Objekten** zurück:
        [
            {{
                "title": "Vollständiger Name oder 'Unbekannt'",
                "betreuer": "Betreuer oder 'Unbekannt'",
                "thema": "Erstes Thema oder 'Unbekannt'"
            }},
            {{
                "title": "Vollständiger Name oder 'Unbekannt'",
                "betreuer": "Betreuer oder 'Unbekannt'",
                "thema": "Zweites Thema oder 'Unbekannt'"
            }}
        ]
        
        **Anzahl der Themen:** {num_source}  
        **Das bedeutet, dass genau {num_source} JSON-Objekte erwartet werden.**

        **Wichtige Hinweise:**
        - Falls eine Information im Text fehlt, setze sie explizit auf **'Unbekannt'**.
        - **Antworte ausschließlich mit JSON – kein zusätzlicher Text oder Erklärungen!**
        - Wenn der Text **keine relevanten Informationen** enthält, antworte mit:
        
        []
        
        **Text:**\n{documents}
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
        print("Model Antwort :-------------------------------------------")
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
    
    # Versuche zuerst, nach einem Array zu suchen
    match = re.search(r'(\[.*\])', clean_string, re.DOTALL)
    
    if match:
        json_data = match.group(1)
        print("Gefundenes JSON-Array :-------------------------------------------")
        print(json_data)
        return json_data
    
    # ein einzelnes JSON-Objekt zu extrahieren
    match_single = re.search(r'(\{.*\})', clean_string, re.DOTALL)
    
    if match_single:
        json_data = match_single.group(1)
        print("Gefundenes einzelnes JSON-Objekt :-------------------------------------------")
        print(json_data)
        return json_data
    
    print("Kein JSON gefunden!")
    return None

# def clean_filename(filename):
#     """Bereinigt den Dateinamen von ungültigen Zeichen für das Dateisystem."""
#     return re.sub(r'[\\/*?:"<>|]', '_', filename)

def save_model_response_to_json(response_data, elapsed_time, num_source, model_folder):
    """Speichert die extrahierten Informationen in einer JSON-Datei."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    cleaned_response = extract_json_from_text(response_data)
    
    try:
        json_data = json.loads(cleaned_response)
        for data in json_data : 
            data["Antwortzeit"] = elapsed_time
            data["Anzahl der untersuchten Dateien"] = num_source
        
        filename ="infos_output.json"
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

# Prüft, wie viele Dateien untersucht werden
unique_sources = set(meta["source"] for meta in vectorstore.get()["metadatas"])
num_sources = len(unique_sources)


# Llama
response_data_model_1, elapsed_time_model1 = extract_information_with_model(Documents, "llama3.1:8b", num_sources)
save_model_response_to_json(response_data_model_1,elapsed_time_model1, num_sources, model_folder="Llama")

#DeepSeek
response_data_model_2,elapsed_time_model2 = extract_information_with_model(Documents, "deepseek-r1:14b", num_sources)
save_model_response_to_json(response_data_model_2, elapsed_time_model2, num_sources, model_folder="DeepSeek")

print(f"Extrahierte Informationen für beide Modelle gespeichert.")