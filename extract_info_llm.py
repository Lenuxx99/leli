import requests
import json
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
import os
import re
import time
import logging

def extract_information_with_model(documents, model_name, num_source):
    """ Extrahiert Name, Betreuer und Thema mithilfe des Modells aus den Dokumenten """
    
    if not documents:
        return json.dumps({"Thema": "Unbekannt, keine Relevante Infos gefunden", "Betreuer": "Unbekannt, keine Relevante Infos gefunden", "Student": "Unbekannt, keine Relevante Infos gefunden"}), "Unbekannt"

    prompt = f"""
        Extrahiere die folgenden Informationen **ausschließlich** aus offiziellen **Bachelorarbeit-Anmeldeformularen**.  
        
        **Typische Informationen in einem Bachelorarbeit-Anmeldeformular:**  
        - **Thema der Bachelorarbeit**  
        - **Name des Studenten & Matrikelnummer**  
        - **Name des Betreuers & E-Mail-Adresse**  

        **Antwortformat:**  
        - Gib die extrahierten Daten **NUR** in **einem oder mehreren JSON-Objekten** aus.  
        - Falls nur eine Anmeldung gefunden wird, gib ein **einzelnes JSON-Objekt** zurück:  

        ```json
        {{
            "Thema": "Thema oder 'Unbekannt'",
            "Betreuer": "Betreuer Name und Email Adresse oder 'Unbekannt'",
            "Student": "Vollständiger Name und Matrikelnummer oder 'Unbekannt'"
        }}
        ```

        - Falls der Text **mehrere Anmeldeformulare** enthält, erstelle eine **Liste von JSON-Objekten**:  

        ```json
        [
            {{
                "Thema": "Erstes Thema oder 'Unbekannt'",
                "Betreuer": "Betreuer Name und Email Adresse oder 'Unbekannt'",
                "Student": "Vollständiger Name und Matrikelnummer oder 'Unbekannt'"
            }},
            {{
                "Thema": "Zweites Thema oder 'Unbekannt'",
                "Betreuer": "Betreuer Name und Email Adresse oder 'Unbekannt'",
                "Student": "Vollständiger Name und Matrikelnummer oder 'Unbekannt'"
            }},
            ...
        ]
        ```

        **Anzahl der erwarteten Anmeldeformulare:** {num_source}  
        *(Genau {num_source} JSON-Objekte werden erwartet, aber nur für relevante Einträge.)*

        **Wichtige Hinweise:**  
        - **Es werden ausschließlich Daten aus offiziellen Bachelorarbeit-Anmeldeformularen extrahiert.**  
        - Falls eine Information im Formular fehlt, setze sie explizit auf **'Unbekannt'**.  
        - **Antworte ausschließlich mit JSON – kein zusätzlicher Text oder Erklärungen!**  
        - Falls der Text **keine relevanten Informationen** enthält, antworte mit: `[]`.  

        **Zusätzliche Bedingung:**  
        - **Alle Inhalte, die nicht aus einem Bachelorarbeit-Anmeldeformular stammen oder nichts mit einer Anmeldung zu tun haben,  
          werden vollständig ignoriert und nicht in die JSON-Antwort aufgenommen.**  

        **Text:**\n{documents}
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
            "Betreuer": "Unbekannt, Modelverbindung fehlgeschlagen",
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