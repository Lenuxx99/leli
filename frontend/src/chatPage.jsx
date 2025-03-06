import React, { useState, useEffect, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';
import './chatPage.css';
import Sidebar from './sidebar.jsx'

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
  const [userInput, setUserInput] = useState({value : "0" , text : ""});
  const [messages, setMessages] = useState([]);
  const messagesEndRef = useRef(null);
  const [Model, setModel] = useState(localStorage.getItem("selectedModel") || "Lama3.1");
  const modelRef = useRef(Model);
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
            { ...lastMessage, complete: true, time: data.time, model : modelRef.current } // Antwort als vollständig markieren
          ];
        }
        return prevMessages;
      });
    });
    socket.on('timeout', () => {
      console.log("Timeout-Event empfangen!");
      setTimeoutState(true)
    });
    socket.on('error', (error) => {
      console.error('Error:', error);
    });
    return () => {
      // Cleanup: Events entfernen
      // Cleanup: Event-Listener entfernen, wenn die Komponente unmountet wird (seite geschlossen)
      socket.off('response');
      socket.off('error');
      socket.off('response_time');
      socket.off('timeout');
    };
  }, []);
  
  // Scrollen bei jeder Änderung von messages
  useEffect(() => {
    scrollToBottom();
    console.log(messages);
  }, [messages]);

  useEffect(() => {
    modelRef.current = Model; // Immer aktualisieren, wenn sich Model ändert
  }, [Model]);
  // User Nachricht absenden
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
    socket.emit('message', { text: userInput.text.trim(), model: Model, file : selectedFile });
  
    setUserInput({ value: "0", text: "" });
  }, [userInput, Model]);  // Abhängigkeiten für sendMessage

  // sende socket Nachricht an der Server wenn der User input sich ändert
  // Bei jedem Render wird sendMessage neu erstellt.
  // Da die Referenz von sendMessage bei jedem Render anders ist, geht React davon aus, dass useEffect erneut ausgeführt werden muss, auch wenn sich userInput nicht geändert hat.
  useEffect(() => {
    if (userInput.value !== "0") {
      sendMessage();
    }
  }, [userInput, sendMessage]);

  const handelevent = (event) => {
    const selectedModel = event.target.value;
    setModel(selectedModel);
    localStorage.setItem("selectedModel", selectedModel);
  };

  const handleContinueRequest = () => {
    setTimeoutState(false); // Timeout-Meldung ausblenden
    socket.emit('continue_request', { text: messages[messages.length - 1].text.trim(), model: Model, file : selectedFile }); // Server auffordern, weiterzumachen
  };

  const handelAbbrechen = () => {
    setTimeoutState(false);
    setMessages((prevMessages) => prevMessages.slice(0, -1)); 
  }
  return (
      <header className="App-header">
        <Sidebar selectedFile={selectedFile} setSelectedFile={setSelectedFile} Model = {Model} /> 
        <div className ="dropdown-container model">
          <select id="options" value = {Model} onChange = {handelevent}>
              <option value="Lama3.1">Lama 3.1</option>
              <option value="DeepSeek">DeepSeek</option>
              <option value="GPT">GPT</option>
          </select>
        </div>  
        <h1>Chat with Our Bot</h1> 
        <div className="formular">
          <div className ="dropdown-container question">
            <select id="options" value = {userInput.value} onChange = {(e) => { 
              setUserInput({ value: e.target.value, text: e.target.options[e.target.selectedIndex].text });
            }}>
              <option value="0">.........</option>
              <option value="1">Welche Thema hat diese Bachelorarbeit?</option>
              <option value="2">Wer ist der Betreuer dieser Bachelorarbeit?</option>
              <option value="3">Von wem wird diese Bachelorarbeit durchgeführt?</option>
            </select>
          </div>  
          <button onClick={sendMessage}>Send</button>
        </div>
        <div className="response-list">
          {messages.map((msg, index) => (
            <div key={index} className={`response-container ${msg.sender === 'user' ? 'user-message' : 'bot-message'}`}>
              <p
                className="response"
                dangerouslySetInnerHTML={{
                  __html: msg.text
                    .replace(/\n/g, '<br>')         // Zeilenumbrüche beibehalten
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'), // Markdown -> HTML
                }}
              ></p>
              {msg.sender === 'bot' && msg.complete && (
                <div className = "infos"><p >⏳ Antwortzeit: {msg.time} Sekunden  </p><p> Model : {msg.model}</p></div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef}></div>
          {timeout && (
            <div className="timeout">
              <p>⚠️ Request timeout: Weiter warten?</p>
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