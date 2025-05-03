import requests
import json
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
import os
import re
import time
import logging

def clean_documents(documents):
    cleaned_docs = []
    for source, text in documents.items():
        # Zeilenumbrüche ersetzen
        text = text.replace("\n", " ")

        # Mehrere Leerzeichen reduzieren
        while "  " in text:
            text = text.replace("  ", " ")

        # Dokument klar trennen
        cleaned_text = f"Dateiname: {source}\nText: {text}\n--- Dokument Ende ---\n"
        cleaned_docs.append(cleaned_text)

    return "\n".join(cleaned_docs)

def extract_information_with_model(documents, model_name, num_source):
    """ Extrahiert Name, Betreuer und Thema mithilfe des Modells aus den Dokumenten """
    
    if not documents:
        return json.dumps({"Thema": "Unbekannt, keine Relevante Infos gefunden", "Betreuer": "Unbekannt, keine Relevante Infos gefunden", "Student": "Unbekannt, keine Relevante Infos gefunden"}), "Unbekannt"
    prepared_documents = clean_documents(documents)
    print("Prompt kontext------------------------------")
    print(prepared_documents)
    prompt = f"""
        **WICHTIG: Halte dich exakt an diese Anweisungen.**

        Du erhältst Hintergrundinformationen, die aus genau **{num_source} Bachelorarbeit-Anmeldeformularen** bestehen.  
        Jedes Anmeldeformular ist im Text durch klare Markierungen voneinander getrennt.  
        Deine Aufgabe ist es, aus **jedem** dieser Formulare folgende Informationen zu extrahieren:

        **Zu extrahierende Informationen pro Anmeldeformular:**
        - **Thema der Bachelorarbeit**
        - **Name des Studenten**
        - **Matrikelnummer des Studenten**
        - **E-Mail-Adresse des Studenten**
        - **Name des Hochschulbetreuers (HS-Betreuer)**
        - **Name des externen Betreuers (Externe Betreuer)**

        **Antwortformat (zwingend einzuhalten!):**
        - Gib ausschließlich **gültigen JSON-Text** zurück.
        - Keine Erklärungen, keine zusätzlichen Sätze, keine Einleitungen, keine Tabellen, keine Kommentare.
        - Nur den reinen JSON-String als Antwort.

        **Format:**
        - Wenn ein Anmeldeformular gefunden wird, antworte mit **einem JSON-Objekt**.
        - Wenn mehrere Anmeldeformulare gefunden werden (was hier der Fall ist), gib eine **Liste von JSON-Objekten** zurück.

        **Struktur eines JSON-Objekts:**

        ```json
        [
        {{
            "Thema": "Thema oder 'Unbekannt' falls nicht vorhanden",
            "Student": "Vollständiger Name oder 'Unbekannt' falls nicht vorhanden",
            "Matrikelnummer": "Matrikelnummer oder 'Unbekannt' falls nicht vorhanden",
            "E-Mail": "E-Mail-Adresse oder 'Unbekannt' falls nicht vorhanden",
            "HS-Betreuer": "Name des Hochschulbetreuers oder 'Unbekannt' falls nicht vorhanden",
            "Externer Betreuer": "Name des externen Betreuers oder 'Unbekannt' falls nicht vorhanden"
        }}
        ]
        """

    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}]
    }
    start_time = time.time()
    try:
        response = requests.post("http://localhost:11434/api/chat", json=payload, stream=True, timeout = 40)
        response_text = ""
        logging.info(f"{model_name} Antwort:")
        if response.status_code == 200:
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    json_data = json.loads(line)
                    logging.info(json_data)
                    if "message" in json_data and "content" in json_data["message"]:
                        response_text += json_data["message"]["content"]  
        end_time = time.time()
        elapsed_time = f"{round(end_time - start_time, 2)}s"
        logging.info(f"Antwortszeit: {elapsed_time}s")
        print("Model Vollantwort :-------------------------------------------")
        print(response_text)
        return response_text, elapsed_time
                 
    except requests.exceptions.Timeout as e:
        print(f"Fehler bei der Anfrage an das Modell: {e}")
        return json.dumps({
            "Thema": "Unbekannt, Modelverbindung fehlgeschlagen",
            "HS-Betreuer": "Unbekannt, Modelverbindung fehlgeschlagen",
            "Student": "Unbekannt, Modelverbindung fehlgeschlagen",
            "Message": "Server timeout",
        }), "Unbekannt"
    

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
        logging.info("In der Modellantwort gefundenes JSON-Array:")
        logging.info(json.loads(json_data))
        return json_data
    
    # ein einzelnes JSON-Objekt zu extrahieren
    match_single = re.search(r'(\{.*\})', clean_string, re.DOTALL)
    
    if match_single:
        json_data = match_single.group(1)
        logging.info("In der Modellantwort gefundenes einzelnes JSON-Objekt:")
        logging.info(json.loads(json_data))
        return json_data
    
    logging.info("Kein JSON gefunden!")
    return {"message": "Es wurde in der Antwort des Modells kein JSON gefunden: Model hat nicht wie gefordert geantwortet"}


def save_model_response_to_json(response_data, elapsed_time, num_source, output_dir, model_folder):
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

        return json_data
    except json.JSONDecodeError as e:
        print(f"Fehler beim Parsen des JSON: {e}")

def save_model_response_to_json_output(response_data, elapsed_time, num_source):
    cleaned_response = extract_json_from_text(response_data)
    
    try:
        if isinstance(cleaned_response, str):  
            json_data = json.loads(cleaned_response)  # String in JSON umwandeln
        else:
            json_data = cleaned_response  # Falls es schon ein Dict oder eine Liste ist, direkt nutzen

        # Falls es ein einzelnes Dict ist, in eine Liste verpacken
        if isinstance(json_data, dict):  
            json_data = [json_data]  

        for data in json_data: 
            data["Antwortzeit"] = elapsed_time
            data["Anzahl der untersuchten Dateien"] = num_source
        
        return json_data
    except json.JSONDecodeError as e:
        print(f"Fehler beim Parsen des JSON: {e}")
        return None 

if __name__ == "__main__":
    
    persist_directory = "chroma_db"

    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embedding_model)
    
    output_dir = 'output_json'
    Documents = vectorstore.get()["documents"]

    unique_sources = set(meta["source"] for meta in vectorstore.get()["metadatas"])
    num_sources = len(unique_sources)

    # Llama
    response_data_model_1, elapsed_time_model1 = extract_information_with_model(Documents, "llama3.1:8b", num_sources)
    save_model_response_to_json(response_data_model_1,elapsed_time_model1, num_sources, output_dir, model_folder="Llama")

    # DeepSeek
    response_data_model_2,elapsed_time_model2 = extract_information_with_model(Documents, "deepseek-r1:14b", num_sources)
    save_model_response_to_json(response_data_model_2, elapsed_time_model2, num_sources, output_dir, model_folder="DeepSeek", )

    print(f"Extrahierte Informationen für beide Modelle gespeichert.")