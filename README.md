PDFs mit LLMs

📚 Beschreibung

Dieses Projekt enthält ein Chatbot-Frontend, das mit React entwickelt wurde, sowie einen Python-Server zur Verarbeitung der Anfragen. Zusätzlich umfasst es eine grafische Benutzeroberfläche zur Extraktion von Informationen aus PDF-Anmeldeformularen zur Bachelorarbeit. Mithilfe des Llama-Algorithmus werden relevante Informationen wie Name, Vorname, Matrikelnummer, Thema und Betreuer extrahiert und als JSON-Datei gespeichert.

Die Benutzeroberfläche soll zudem eine Auswahl an vorgefertigten Fragen bereitstellen, um verschiedene Testfälle zu ermöglichen. Zusätzlich können Benutzer zwischen verschiedenen Modellen wählen und Parameter individuell anpassen.

👨‍💻 Voraussetzungen

Stelle sicher, dass du folgende Software und Bibliotheken installiert hast:

Python 3.8+

pip (Python-Paketmanager)

Ollama (zur Ausführung der LLMs)

ChromaDB (Vektordatenbank zur Speicherung der Embeddings)

Node.js & npm (für das React-Frontend)

📦 Installation

1️⃣ Python-Umgebung einrichten

Erstelle eine virtuelle Umgebung (optional):

python -m venv venv

venv\Scripts\activate  # Für Windows

2️⃣ Erforderliche Abhängigkeiten installieren

pip install -r requirements.txt

3️⃣ Ollama installieren und starten

Lade Ollama herunter und installiere es. Starte anschließend den Server:

ollama serve

📂 Nutzung

1️⃣ PDFs in ChromaDB laden

Führe das Skript aus:

python Embeddings.py

Speichere deine PDFs im Ordner pdf_files/, um die Inhalte in Embeddings umzuwandeln und in der Chroma-Datenbank zu speichern.

2️⃣ Informationen extrahieren

Starte das Hauptskript zur Extraktion der Informationen:

python extract_info.py

3️⃣ Ergebnisse überprüfen

Die extrahierten Daten werden als JSON-Dateien im output_json/ Ordner gespeichert.

🏆 Start von React-App

1️⃣ React-Frontend für Produktion bauen

Navigiere in den react-Ordner und führe den folgenden Befehl aus, um ein Produktions-Build zu erstellen:

cd chatbot-frontend

npm install

npm run build

Dadurch wird ein build/-Ordner erstellt, der vom Server verwendet wird. Zudem ist React als Proxy in der package.json-Datei definiert, sodass API-Anfragen während der Entwicklung direkt an den Flask-Server weitergeleitet werden (nur lokal). Das Routing übernimmt React vollständig, während die Flask-App immer nur die index.html-Seite zurückgibt(SPA).

2️⃣ Python-Server starten

Wechsle zurück zum Hauptverzeichnis und starte den Server mit:

cd ..

python server.py

Dadurch wird der Server gestartet und das Frontend aus dem build/-Ordner unter dem Port 5000 ausgeliefert.

🛠 Fehlerbehebung

Falls npm run build nicht funktioniert:

Stelle sicher, dass Node.js und npm installiert sind (node -v und npm -v prüfen).

Falls Pakete fehlen, führe npm install im react-Ordner aus.

Falls python server.py nicht funktioniert:

Stelle sicher, dass Python installiert ist (python --version prüfen).

Falls Abhängigkeiten fehlen, installiere sie mit pip install -r requirements.txt.

Falls ollama serve nicht läuft:

Starte den Server mit ollama serve

Falls ChromaDB Fehler auftreten:

Lösche den chroma_db/ Ordner und starte python Embeddings.py neu

Falls Modelle fehlen:

Stelle sicher, dass llama3.1:8b oder deepseek-r1:14b in Ollama verfügbar sind

🏆 Fazit

Nach dem Build kannst du die Anwendung einfach mit python server.py starten, und dein Chatbot läuft im Produktionsmodus! Zusätzlich kannst du PDFs analysieren und extrahierte Daten in JSON speichern. 🚀




runi e server w jawek bhy ye zzzzz



