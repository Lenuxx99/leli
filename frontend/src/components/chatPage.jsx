import React, { useState, useEffect, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';
import '../styles/chatPage.css';
import Sidebar from './sidebar.jsx';
import TestModels from './test_models.jsx';

// In der Entwicklungsumgebung (`npm run dev`) kann in der `package.json` ein Proxy definiert werden, z. B.:
// "proxy": "http://localhost:5000"
// Dadurch werden alle API- und WebSocket-Anfragen automatisch an den Backend-Server weitergeleitet, 
// sodass die Server-URL hier nicht explizit angegeben werden muss.
//
// In der Produktionsumgebung (nach `npm run build`) läuft die React-App und das Backend auf derselben Domain,
// sodass `io()` ebenfalls automatisch die richtige Verbindung herstellt.
//
// Falls kein Proxy verwendet wird oder das Backend eine andere Domain hat, muss die Server-URL explizit angegeben werden, z. B.:
// const socket = io('http://localhost:5000');  // Nur erforderlich, wenn kein Proxy genutzt wird.
const socket = io("http://localhost:5000/");

function ChatPage() {
  const [userInput, setUserInput] = useState({ value: "0", text: "" });
  const [Input, setInput] = useState("");
  const [showOptions, setShowOptions] = useState(false)
  const [messages, setMessages] = useState([]);
  const messagesEndRef = useRef(null);
  const [Model, setModel] = useState(localStorage.getItem("selectedModel") || "Lama3.1");
  const [timeout, setTimeoutState] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  // Automatisches Scrollen
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Socket-Events registrieren
  useEffect(() => {
    // Die Socket-Verbindung wird geöffnet, sobald die Komponente gerendert wird,
    // Event-Listener: Die Callback-Funktion wird ausgeführt, wenn eine Nachricht ankommt (läuft asynchron).
    socket.on('response', (data) => {
      setMessages((prevMessages) => {
        const lastMessage = prevMessages[prevMessages.length - 1];
        if (lastMessage && lastMessage.sender === 'bot' && !lastMessage.complete) {
          // letzte Bot-Nachricht noch unvollständig -> text anhängen
          return [
            ...prevMessages.slice(0, -1),
            { ...lastMessage, text: lastMessage.text + data.response },
          ];
        }
        // Falls die letzte Nachricht vom User stammt, wird eine neue Bot-Nachricht erstellt.
        return [...prevMessages, { sender: 'bot', text: data.response, complete: false }];
      });
    });
    socket.on('response_time', (data) => {
      setMessages((prevMessages) => {
        const lastMessage = prevMessages[prevMessages.length - 1];
        if (lastMessage && lastMessage.sender === 'bot') {
          // Markiert die letzte Bot-Nachricht als vollständig und speichert die Antwortzeit sowie das Modell.
          return [
            ...prevMessages.slice(0, -1), // enfernt letzte element des Arrays
            { ...lastMessage, complete: true, time: data.time, model: data.model } // Antwort als vollständig markieren
          ];
        }
        return prevMessages;
      });
    });
    socket.on('timeout', () => {
      console.log("Timeout-Event empfangen!");
      setTimeoutState(true)
    });
    // in Produktion wird nicht benötigt
    socket.on("connect", () => {
      console.log("Verbunden mit dem Server", socket.id);
    });

    socket.on("connect_error", (error) => {
      console.error("Verbindung fehlgeschlagen:", error);
      alert("Verbindung zum Server fehlgeschlagen. Bitte überprüfe die Verbindung.");
    });

    socket.on("disconnect", (reason) => {
      console.warn("⚠️ Verbindung getrennt:", reason);
    });
    socket.on('error', (error) => {
      console.error('Error:', error.error);
      alert(error.error);
    });
    return () => {
      // Cleanup: Events entfernen
      // Cleanup: Event-Listener entfernen, wenn die Komponente unmountet wird (seite geschlossen)
      socket.off('response');
      socket.off('error');
      socket.off('response_time');
      socket.off('timeout');
      socket.off("connect");
      socket.off("connect_error");
      socket.off("disconnect");
    };
  }, []);

  // Scrollen bei jeder Änderung von messages
  useEffect(() => {
    scrollToBottom();
    console.log(messages);
  }, [messages]);

  // User Nachricht absenden (Dropdown Nachrichten)
  // useCallback ist ein React-Hook, der eine memoisierte Version der Funktion zurückgibt. 
  // Das bedeutet, dass die Funktion nur dann neu erstellt wird, wenn eine ihrer Abhängigkeiten sich geändert hat. 
  // Andernfalls gibt useCallback die alte Referenz der Funktion zurück, was bedeutet, dass die Funktion stabil bleibt und nicht bei jedem Render neu erstellt wird.
  const sendMessage = useCallback(() => {
    if (!userInput.text.trim() || userInput.value === "0" || timeout) {   // wenn timeout Nachricht gezeigt wird, könnte man keine weitere nachrichten geben
      setUserInput({ value: "0", text: "" });
      return;
    }
    const lastMessage = messages[messages.length - 1]; // Letzte Nachricht holen

    if (lastMessage) {
      if (lastMessage.sender === "bot" && !lastMessage.complete) {
        setUserInput({ value: "0", text: "" });
        return; // Falls die letzte Bot-Nachricht noch nicht fertig ist
      }
      if (lastMessage.sender === "user") {
        setUserInput({ value: "0", text: "" });
        return; // Falls die letzte Nachricht vom User ist (keine Doppel-Sends)
      }
    }

    // User-Nachricht in den State
    setMessages((prevMessages) => {
      const newMessages = [...prevMessages, { sender: 'user', text: userInput.text.trim() }];
      return newMessages;
    });
    // setMessages((prev) => [...prev, { sender: 'user', text: userInput.text.trim() }]);

    // An den Server via Socket.IO
    socket.emit('message', { text: userInput.text.trim(), model: Model, file: selectedFile });

    setUserInput({ value: "0", text: "" });
  }, [userInput]);  // Abhängigkeiten für sendMessage

  // sende socket Nachricht an der Server direkt wenn der userInput sich ändert
  // Bei jedem Render wird sendMessage neu erstellt.
  // Da die Referenz von sendMessage bei jedem Render anders ist, geht React davon aus, dass useEffect erneut ausgeführt werden muss, auch wenn sich userInput nicht geändert hat.
  useEffect(() => {
    if (userInput.value !== "0") {
      sendMessage();
    }
  }, [userInput, sendMessage]);

  // TextInput Nachrichten
  const sendTextInputMessage = () => {
    if (!Input.trim() || timeout) {   // wenn timeout Nachricht gezeigt wird, könnte man keine weitere nachrichten geben
      setInput("");
      return;
    }
    const lastMessage = messages[messages.length - 1]; // Letzte Nachricht holen

    if (lastMessage) {
      if (lastMessage.sender === "bot" && !lastMessage.complete) {
        setInput("");
        return; // Falls die letzte Bot-Nachricht noch nicht fertig ist
      }
      if (lastMessage.sender === "user") {
        setInput("");
        return; // Falls die letzte Nachricht vom User ist (keine Doppel-Sends)
      }
    }
    setMessages((prevMessages) => {
      const newMessages = [...prevMessages, { sender: 'user', text: Input.trim() }];
      return newMessages;
    });
    // setMessages((prev) => [...prev, { sender: 'user', text: userInput.text.trim() }]);

    // An den Server via Socket.IO
    socket.emit('message', { text: Input.trim(), model: Model, file: selectedFile });
    setInput("");
  }

  // options-container (Dropdwon Questions) wird ausgeblendet wenn ausßerhalb von userinput geklickt wird
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (!event.target.closest(".userInput")) {
        setShowOptions(false);
      }
    };

    document.addEventListener("click", handleClickOutside);
    return () => {
      document.removeEventListener("click", handleClickOutside);
    };
  }, []);

  const handelChangeModel = (event) => {
    const selectedModel = event.target.value;
    setModel(selectedModel);
    localStorage.setItem("selectedModel", selectedModel);
  };

  const handleContinueRequest = () => {
    setTimeoutState(false);
    socket.emit('continue_request', { text: messages[messages.length - 1].text.trim(), model: Model, file: selectedFile }); // Server auffordern, weiterzumachen
  };

  const handelAbbrechen = () => {
    setTimeoutState(false);
    setMessages((prevMessages) => prevMessages.slice(0, -1));
  }
  return (
    <header className="App-header">
      <Sidebar selectedFile={selectedFile} setSelectedFile={setSelectedFile} Model={Model} />
      <div className="dropdown-container model">
        <select id="options" value={Model} onChange={handelChangeModel}>
          <option value="Lama3.1">Lama 3.1</option>
          <option value="DeepSeek">DeepSeek</option>
          <option value="Mistral">Mistral</option>
        </select>
        <TestModels selectedFile={selectedFile} />
      </div>
      <h1 style={{ marginTop: "100px", color: "goldenrod" }} >LLMs Test Umgebung</h1>
      <div className="hinweise">
        <p><strong>Hinweise zur Nutzung:</strong></p>
        <ul>
          <li>Wähle ein Modell im Dropdown-Menü oben rechts.</li>
          <li>Lade eine PDF-Datei über die <strong>Seitenleiste rechts</strong> hoch und wählen sie dies aus.</li>
          <li>Nutze die vorgeschlagenen Fragen oder stelle eigene Fragen im Eingabefeld.</li>
        </ul>
      </div>
      <h2 style = {{ fontSize: "1.5rem"}}>PDF Abfragen</h2>
      <div className="formular">
        <div className="userInput">
          <input
            type="text"
            placeholder="Schreibe etwas..."
            value={Input}
            onFocus={() => setShowOptions(true)}
            onChange={(e) => {
              setInput(e.target.value);
              setShowOptions(e.target.value === "");
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault(); // Verhindert einen Zeilenumbruch im Input-Feld
                sendTextInputMessage();
              }
            }}
          />
          {showOptions && userInput.text === "" && (
            <div className="options-container">
              <div
                className="option"
                onClick={() => setUserInput({ value: "1", text: "Welches Thema hat diese Bachelorarbeit?" })}
              >
                Welches Thema hat diese Bachelorarbeit?
              </div>
              <div
                className="option"
                onClick={() => setUserInput({ value: "2", text: "Wer ist der Betreuer dieser Bachelorarbeit?" })}
              >
                Wer ist der Betreuer dieser Bachelorarbeit?
              </div>
              <div
                className="option"
                onClick={() => setUserInput({ value: "3", text: "Von wem wird diese Bachelorarbeit durchgeführt?" })}
              >
                Von wem wird diese Bachelorarbeit durchgeführt?
              </div>
            </div>
          )}
          {messages.length > 0 &&
            messages[messages.length - 1].sender === "user" && !timeout  &&
            !messages.some((msg, index) => index > messages.findLastIndex(m => m.sender === "user") && msg.sender === "bot") && (
              <div className="thinking-indicator">🤔 Denkprozess läuft...</div>
            )}
        </div>
        <button onClick={sendTextInputMessage}>Send</button>
      </div>



      <div className="response-list">
        {messages.map((msg, index) => (
          <div key={index} className={`response-container ${msg.sender === 'user' ? 'user-message' : 'bot-message'}`}>
            <p
              className="response"
              dangerouslySetInnerHTML={{
                __html: msg.text
                  .replace(/\n/g, '<br>')                             // Zeilenumbrüche beibehalten
                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'),  // Markdown -> HTML
              }}
            ></p>
            {msg.sender === 'bot' && msg.complete && (
              <div className="infos"><p >⏳ Antwortzeit: {msg.time} Sekunden  </p><p> Model : {msg.model}</p></div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef}></div>
        {timeout && (
          <div className="timeout">
            <p>⚠️ Request timeout: Anfrage erneut senden?</p>
            <div className="timeout-buttons">
              <button className="cancel" onClick={handelAbbrechen}>❌</button>
              <button className="confirm" onClick={handleContinueRequest}>✅</button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}

export default ChatPage;