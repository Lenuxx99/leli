import time
import json
import requests
import csv
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
import logging

def query_model(model_name, question, context):
    """Sendet eine Anfrage an das Modell und misst die Antwortzeiten."""
    try:
        full_prompt = f"""
            Bitte beantworte die folgende Frage präzise und knapp, basierend ausschließlich auf den bereitgestellten Informationen.
            Integriere die relevanten Inhalte direkt in deine Antwort, ohne darauf hinzuweisen, dass sie aus einer externen Quelle stammen.
            
            Falls die bereitgestellten Informationen keine passende Antwort ermöglichen, antworte mit:  
            **"Die ausgewählte PDF enthält keine relevanten Informationen zur Beantwortung der Frage."**

            Die Antwort sollte logisch, präzise und themenbezogen sein.

            **Wichtig:**  
            - Antworte in der Sprache, in der die Frage gestellt wurde.
            - Keine zusätzlichen Erklärungen oder Hinweise auf Quellen.

            **Hintergrundinformationen:**  
            {context}

            **Frage:**  
            {question}
        """
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": full_prompt}]
        }
        start_request_time = time.time()  # Zeitpunkt der Anfrage
        # Methode	        Modell Berechnung	                                Senden an Client	                    Vorteil
        # stream=True	    Stückweise während des Sendens	                    Token für Token	Frühe Antwort,          Echtzeit-Effekt
        # stream=False	    Alles auf einmal, komplette Berechnung zuerst	    Alles auf einmal	                    Weniger Netzwerk-Overhead
        # 📌 Vergleich der Antwortzeit (ohne Rechenzeit des Modells)
        # Methode	                            Netzwerkaufrufe	Latenz pro Aufruf	Gesamtlatenz
        # stream=True (Token für Token)	        50 (für 50 Tokens)	200 ms	        10 Sekunden
        # stream=False (einmal senden)	        1	200 ms	                        200 ms

        start_request_time = time.time()

        response = requests.post("http://localhost:11434/api/chat", json=payload, stream=False, timeout=20)
        
        if response.status_code != 200:
            return ["Fehler", "Fehler", "Fehler"], ""

        end_time = time.time()  # Modell hat komplette Antwort generiert

        response_text = ""
        json_strings = response.text.strip().split("\n") # gibt eine reihe von json
        for json_str in json_strings:
            try:
                json_data = json.loads(json_str)
                if "message" in json_data and "content" in json_data["message"]:
                    response_text += json_data["message"]["content"] 
                logging.info(json_data)  # Debugging
            except json.JSONDecodeError as e:
                print("Fehler beim JSON-Parsing:", e)

        # Zeiten berechnen
        model_processing_time = round(end_time - start_request_time, 2)  # Zeit bis zur fertigen Antwort

        return f"{model_processing_time}s", response_text
        # first_response = True
        # start_generation_time = None  # Zeitpunkt, wenn das Modell beginnt zu antworten
        # end_time = None  # Zeitpunkt des letzten Tokens
        # response = ""

        # for line in response.iter_lines(decode_unicode=True):
        #     if line:
        #         json_data = json.loads(line)

        #         if "message" in json_data and "content" in json_data["message"]:
        #             if first_response:
        #                 start_generation_time = time.time()  # Modell hat erstes Token generiert
        #                 first_response = False
                    
        #             token = json_data["message"]["content"] 
        #             response += token
        #             # print(token, end="", flush=True)
                    
        #             end_time = time.time()  # Aktualisiert sich mit jedem Token

        # if start_generation_time and end_time:
        #     model_processing_time = round(start_generation_time - start_request_time, 2)  # Zeit bis erstes Token
        #     model_response_time = round(end_time - start_generation_time, 2)  # Zeit für restliche Antwort
        #     total_time = model_processing_time + model_response_time  # Gesamtzeit
        #     # start_request_time → Startzeit, wenn die Anfrage gesendet wird.
        #     # start_generation_time → Sobald das erste Token empfangen wird.
        #     # end_time → Letztes Token wird empfangen.
        #     print(f"\n[{model_name}] '{question}'")
        #     print(f"   Modell-Berechnungszeit (bis erstes Token): {model_processing_time}s")
        #     print(f"   Modell-Antwortzeit (komplette Antwort): {model_response_time}s")
        #     print(f"   Gesamtzeit: {total_time}s\n")

        #     return [model_processing_time, model_response_time, total_time], response
    
    except requests.exceptions.Timeout:
        return "⚠️ Timeout", "keine response generiert"



if __name__ == "__main__":
    models = [
        "llama3.1:8b",
        "deepseek-r1:8b",
        "mistral"
    ]

    # Testfragen (Kriterien für die CSV-Spalten)
    questions = ["Thema?", "Betreuer Name?", "Supervisor name?", "Betreuer E-Mail?"]

    # CSV-Datei für die Ergebnisse
    output_file = "model_vergleich.csv"
    persist_directory = "chroma_db"


    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    vectorstore = Chroma(persist_directory=persist_directory, embedding_function=embedding_model)

    results = []

    for model_name in models:
        row = [model_name]  # Erste Spalte: Modellname
        for question in questions:
            times, response = query_model(model_name, question) 
            row.extend(times)  # Zeiten in die Zeile einfügen
        results.append(row)

    # CSV-Datei speichern
    with open(output_file, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        
        # Kopfzeile schreiben
        header = ["Modell"]
        for question in questions:
            header.extend([f"{question} - Berechnungszeit in s", f"{question} - Antwortszeit in s", f"{question} - Gesamt in s"])
        writer.writerow(header)
        
        # Ergebnisse schreiben
        writer.writerows(results)

    print(f"✅ Ergebnisse gespeichert in {output_file}")