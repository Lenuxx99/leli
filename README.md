# PDFs mit LLMs

## 📚 Beschreibung
Dieses Projekt enthält ein Chatbot-Frontend, das mit React entwickelt wurde, sowie einen Python-Server zur Verarbeitung der Anfragen. Zusätzlich umfasst es eine grafische Benutzeroberfläche zur Extraktion von Informationen aus PDF-Anmeldeformularen zur Bachelorarbeit. Mithilfe des Llama-Algorithmus werden relevante Informationen wie Name, Vorname, Matrikelnummer, Thema und Betreuer extrahiert und als JSON-Datei gespeichert.

Die Benutzeroberfläche soll zudem eine Auswahl an vorgefertigten Fragen bereitstellen, um verschiedene Testfälle zu ermöglichen. Zusätzlich können Benutzer zwischen verschiedenen Modellen wählen und Parameter individuell anpassen.

## 👨‍💻 Voraussetzungen
Stelle sicher, dass du folgende Software und Bibliotheken installiert hast:

* Python 3.8+
* pip (Python-Paketmanager)
* Ollama (zur Ausführung der LLMs)
* Node.js & npm (für das React-Frontend)
* Windows-Betriebssystem

## 📦 Installation

### 1️⃣ Python-Umgebung einrichten
Erstelle eine virtuelle Umgebung (optional):

```
$ python -m venv venv
$ venv\Scripts\activate  # Für Windows
```

### 2️⃣ Erforderliche Abhängigkeiten installieren

```
$ pip install -r requirements.txt
```
Haupt-Pakete:

* Flask-SocketIO==5.5.1
* langchain-community==0.3.18
* pipdeptree
* chromadb==0.6.3
* sentence-transformers==3.4.1

### 3️⃣ Ollama installieren und starten
Lade Ollama herunter und installiere es.

Installiere die beiden Modelle:

```
$ ollama run deepseek-r1:14b
$ ollama run llama3.1:8b
```

Starte anschließend den Server, falls er noch nicht gestartet ist:

```
$ ollama serve
```

## 📂 Nutzung

### 1️⃣ PDFs in ChromaDB laden
Führe das Skript aus:

```
$ python Embeddings.py
```

Speichere deine PDFs im Ordner `pdf_files/`, um die Inhalte in Embeddings umzuwandeln und in der Chroma-Datenbank zu speichern.

### 2️⃣ Informationen extrahieren
Starte das Hauptskript zur Extraktion der Informationen:

```
$ python extract_info.py
```

### 3️⃣ Ergebnisse überprüfen
Die extrahierten Daten werden als JSON-Dateien im `output_json/` Ordner gespeichert.

## 🏆 Start von React-App

### 1️⃣ React-Frontend für Produktion bauen

```
$ cd frontend
$ npm install
$ npm run build
```

Dadurch wird ein `dist/`-Ordner erstellt, der vom Server verwendet wird. Zudem ist React als Proxy in der package.json-Datei definiert, sodass API-Anfragen während der Entwicklung direkt an den Flask-Server weitergeleitet werden (nur lokal).In Produktion übernimmt React Das Routing vollständig, während die Flask-App immer nur die index.html-Seite zurückgibt(SPA).

### 2️⃣ Python-Server starten
Wechsle zurück zum Hauptverzeichnis und starte den Server mit:

```
$ cd ..
$ python server.py
```

Dadurch wird der Server gestartet und das Frontend aus dem `dist/`-Ordner unter dem Port 5173 ausgeliefert.

## 🛠 Fehlerbehebung

Falls `npm run build` nicht funktioniert:
* Stelle sicher, dass Node.js und npm installiert sind (`node -v` und `npm -v` prüfen).
* Falls Pakete fehlen, führe `npm install` im react-Ordner aus.
* Node Version: 18.18.0 oder neuer

Falls `python server.py` nicht funktioniert:
* Stelle sicher, dass Python installiert ist (`python --version` prüfen).
* Falls Abhängigkeiten fehlen, installiere sie mit `pip install -r requirements.txt`.

Falls `ollama serve` nicht läuft:
* Starte den Server mit `ollama serve`

Falls ChromaDB Fehler auftreten:
* Lösche den `chroma_db/` Ordner und starte `python Embeddings.py` neu

Falls Modelle fehlen:
* Stelle sicher, dass `llama3.1:8b` oder `deepseek-r1:14b` in Ollama verfügbar sind

## Entwicklungsumgebung vs. Produktionsumgebung

### Entwicklungsumgebung:
* React läuft im Entwicklungsmodus (`npm run dev`) auf einem lokalen Server (meistens http://localhost:5173)
* Flask läuft auf einem separaten Server (meistens http://localhost:5000)
* Hot Reloading: Änderungen an der React-App führen zu einer sofortigen Aktualisierung der Anzeige ohne manuelles Laden
* CORS: CORS-Probleme treten auf, wenn Frontend und Backend auf verschiedenen Ports laufen. CORS muss erlaubt, um diese Anfragen zu ermöglichen

### Produktionsumgebung:
* React wird gebaut (`npm run build`), und die statischen Dateien werden von einem Webserver bereitgestellt
* Flask und React laufen eventuell auf denselben Servern oder unter dem gleichen Domains/Ports
* Keine Hot Reloading: Im Produktionsmodus sind keine automatischen Updates mehr vorhanden
* CORS ist oft weniger problematisch, da das Frontend und Backend in einer gemeinsamen Domain/Dienst bereitgestellt werden

### Vorteile:
* Kein Reverse-Proxy erforderlich: Flask kann dazu verwenden, sowohl das Frontend (React) als auch das Backend (Flask) auf demselben Server zu betreiben, ohne einen Reverse-Proxy wie NGINX zu verwenden.
* Einfachheit: Diese Lösung ist einfach und eignet sich gut für kleinere Produktionsumgebungen oder wenn du keine zusätzliche Komplexität durch NGINX einführen möchtest.

### Wann wird NGINX trotzdem sinnvoll?
* Performance: NGINX bietet erweiterte Funktionen wie Caching, Lastenverteilung, und optimierte Handhabung von statischen Dateien, was für größere Anwendungen wichtig sein kann.
* SSL/TLS und Sicherheitsfeatures: NGINX kann SSL/TLS-Verbindungen handhaben und zusätzliche Sicherheitsfunktionen bieten.
* Trennung von Diensten: Wenn du in Zukunft das Frontend und das Backend auf verschiedenen Servern oder in verschiedenen Containern betreiben möchtest, kann NGINX helfen, den Verkehr zwischen den beiden zu vermitteln und Lasten auszugleichen.

## 🏆 Fazit
Nach dem Build kannst du die Anwendung einfach mit `python server.py` starten, die anwendung läuft im Produktionsmodus! Zusätzlich kannst du PDFs analysieren und extrahierte Daten in JSON speichern. 🚀


runi e server w jawek bhy ye zzzzz
