import time
import json
import logging
import psutil 
import asyncio
import aiohttp
import re
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key = api_key)
# Methode	        Modell Berechnung	                                Senden an Client	                    Vorteil
# stream=True	    Stückweise während des Sendens	                    Token für Token	Frühe Antwort,          Echtzeit-Effekt
# stream=False	    Alles auf einmal, komplette Berechnung zuerst	    Alles auf einmal	                    Weniger Netzwerk-Overhead
# 📌 Vergleich der Antwortzeit (ohne Rechenzeit des Modells)
# Methode	                            Netzwerkaufrufe	Latenz pro Aufruf	Gesamtlatenz
# stream=True (Token für Token)	        50 (für 50 Tokens)	200 ms	        10 Sekunden
# stream=False (einmal senden)	        1	200 ms	                        200 ms

async def monitor_system(stop_event, results):
    """Überwacht die CPU- und RAM-Auslastung während der Anfrage und berechnet den Durchschnitt"""
    cpu_values = []
    ram_values = []

    while not stop_event.is_set():
        cpu_during = psutil.cpu_percent(interval=None)
        ram_during = psutil.virtual_memory().percent
        
        cpu_values.append(cpu_during)
        ram_values.append(ram_during)

        logging.info(f"Während der Anfrage - CPU: {cpu_during}%, RAM: {ram_during}%")
        await asyncio.sleep(1)

    results["avg_cpu"] = sum(cpu_values) / len(cpu_values) if cpu_values else 0
    results["avg_ram"] = sum(ram_values) / len(ram_values) if ram_values else 0


async def query_model(model_name, question, context):
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
        payload = {"model": model_name, "messages": [{"role": "user", "content": full_prompt}]}
        url = "http://localhost:11434/api/chat"

        stop_event = asyncio.Event()
        results = {}

        # Starte das CPU/RAM-Monitoring parallel
        monitor_task = asyncio.create_task(monitor_system(stop_event, results))
        start_request_time = time.time()

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=20) as response:
                if response.status != 200:
                    stop_event.set()  # Überwachung beenden
                    await monitor_task  
                    return ["Fehler", "Fehler", "Fehler"], ""

                json_strings = await response.text()

                stop_event.set()
                await monitor_task 
                end_time = time.time()

                json_strings = json_strings.strip().split("\n")  # Zeilenweises JSON

                response_text = ""
                for json_str in json_strings:
                    try:
                        json_data = json.loads(json_str)
                        if "message" in json_data and "content" in json_data["message"]:
                            response_text += json_data["message"]["content"]
                        logging.info(json_data)  
                    except json.JSONDecodeError as e:
                        print("Fehler beim JSON-Parsing:", e)
 
        model_processing_time = round(end_time - start_request_time, 2)
        logging.info(f"Modell-Antwortszeit (bis komplette Antwort): {model_processing_time}")

        avg_cpu = results.get("avg_cpu", 0)
        avg_ram = results.get("avg_ram", 0)

        return f"{model_processing_time}s", response_text, f"Durchschnittliche CPU: {avg_cpu:.2f}%, RAM: {avg_ram:.2f}%"

    except asyncio.TimeoutError:
        return "⚠️ Timeout", "keine Antwort", "CPU/RAM nicht verfügbar"

def extract_json_from_text(text):
    """ Extrahiert das JSON aus einer Textantwort, falls zusätzliches Rauschen vorhanden ist. """
    match = re.search(r"\{.*\}", text, re.DOTALL)  # Sucht nach JSON-ähnlichem Text
    if match:
        return match.group(0)  # Gibt nur das gefundene JSON zurück
    return "{'message' : 'Kein JSON in der Bewertungsantwort des Model gefunden'}" 

def evaluate_response(model_answer, Erwartete_Inhalte, referenz, question):
    prompt = f"""
        Bewerte die folgende Antwort auf die gestellte Frage und gib das Ergebnis als JSON zurück.

        ### **Gestellte Frage:**  
        {question}  

        ### **Modellantwort:**  
        {model_answer}  

        ### **Erwartete Inhalte:**  
        {Erwartete_Inhalte}  
        Überprüfe, ob die Modellantwort die erwarteten Inhalte enthält.

        ### **Referenz:**
        {referenz}
        ---

        ## **📌 Bewertungskriterien (1-10):**
        - **Genauigkeit:** Enthält die Antwort die erwarteten Informationen **exakt und korrekt**?
        - **Vollständigkeit:** Beantwortet die Antwort **vollständig**, ohne Teile der erwarteten Antwort auszulassen?
        - **Relevanz:** Enthält die Antwort **nur relevante Informationen zur Frage**?  
        - **Alles, was nicht direkt zur Frage gehört, senkt die Bewertung stark!**  
        - Beispiele für irrelevante Inhalte:  
            - **Denkanweisungen** (z. B. "Ich denke, dass...","<think>...</think>")  
            - **Interne Überlegungen** (z. B. "Die beste Antwort wäre...")  
            - **Zusätzliche Informationen** (z. B. unnötige Beschreibungen oder Kontext, der nicht gefordert wurde)  
            - **Wiederholungen oder lange Antworten**  
        - **Klarheit & Natürlichkeit:** Ist die Antwort **kurz, klar und präzise formuliert**?

        ### **⚠️ Besondere Anweisung für die Bewertung:**  
        - **Perfekte Antworten sind kurz und direkt!**  
        - **Beispiel Frage:** *"Welcher Betreuer hat die Bachelorarbeit?"*  
        - **Perfekte Antwort:** *"Herr Ulrich ist der Betreuer der Bachelorarbeit."*  
        - **Jede zusätliche Informationen zu dieser Antwort gilt als redundant und senkt die Note für Relevanz!**  

        ---

        ### **📌 Format der JSON-Antwort:**  
        Gib die Bewertung als JSON zurück, in genau diesem Format:
        ```json
        {{
            "Note (/10)": note,
            "Bewertungskriterien": {{
                "Genauigkeit": {{"Note": note, "Grund": "kurze Erklärung"}},
                "Vollständigkeit": {{"Note": note, "Grund": "kurze Erklärung"}},
                "Relevanz": {{"Note": note, "Grund": "kurze Erklärung"}},
                "Klarheit & Natürlichkeit": {{"Note": note, "Grund": "kurze Erklärung"}}
            }}
        }}
        """
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        logging.info("gpt-4o-mini Antwort (Auswertung):")
        
        json_output = extract_json_from_text(completion.choices[0].message.content)

        logging.info(json.loads(json_output))
        return json.loads(json_output)  
    except Exception as e:
        print(f"Fehler: {e}") 
        return {"message": "Modelverbindung fehlgeschlagen"}
    # response = requests.post(
    #     "http://localhost:11434/api/chat",
    #     json={"model": "llama3.1:8b", "messages": [{"role": "user", "content": prompt}]}
    # )

    # if response.status_code != 200:
    #     logging.info(f"Fehler: {response.status_code}, {response.text}")
    #     return {"message" : "Modelverbindung fehlgeschlagen"}

    # logging.info("Model Auswertung Antwort:")
    # try:
    #     response_text = ""
    #     json_data = response.text.strip().split("\n")  # Falls die API JSONL zurückgibt

    #     for token in json_data:
    #         token_json = json.loads(token)  
    #         logging.info(token_json)
    #         if "message" in token_json and "content" in token_json["message"]:
    #             response_text += token_json["message"]["content"]

    #     json_output = extract_json_from_text(response_text)  # Extrahiert nur das JSON
    #     return json.loads(json_output)

    # except json.JSONDecodeError as e:
    #     logging.info("Fehler beim Parsen der JSON-Daten:", e)
    #     logging.info("Rohdaten:", response.text)
    #     return {"message" : "Fehler beim Parsen der JSON-Daten"}
    


async def main():
    model = "llama3.1:8b"
    question = "Was ist maschinelles Lernen?"
    context = "Maschinelles Lernen ist ein Teilbereich der künstlichen Intelligenz."
    
    result = await query_model(model, question, context)
    print(result)

    question = "welche betreuer hat diese Bachelorarbeit"
    model_answer = "Die Bachelorarbeit Thema ist LLM und wird von Herr Munster betreut"
    reference = "der Betreuer ist... (muss der name des betreuer enthalten sein)"

    score = evaluate_response(model_answer, reference, question)
    print(f"Modellbewertung: {score}")


if __name__ == "__main__":
    asyncio.run(main())
