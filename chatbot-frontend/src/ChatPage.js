import React, { useState, useEffect, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';
import './ChatPage.css';

// Socket-Verbindung aufbauen.
// Achten Sie darauf, die richtige URL/Port zu verwenden, wo Flask-SocketIO läuft:
const socket = io('http://localhost:5000');

function ChatPage() {
  const [userInput, setUserInput] = useState({value : "0" , text : ""});
  const [messages, setMessages] = useState([]);
  const messagesEndRef = useRef(null);
  const [Model, setModel] = useState(localStorage.getItem("selectedModel") || "Lama3.1");
  const modelRef = useRef(Model); // Referenz für Model

  useEffect(() => {
    modelRef.current = Model; // Immer aktualisieren, wenn sich Model ändert
  }, [Model]);

  // Automatisches Scrollen
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Socket-Events registrieren
  useEffect(() => {
    // Wenn vom Server eine Antwort kommt
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
        // neue Bot-Nachricht, wenn der letzte nachricht von User ist 
        return [...prevMessages, { sender: 'bot', text: data.response, complete: false }];
      });
    });
    socket.on('response_time', (data) => {
      setMessages((prevMessages) => {
        const lastMessage = prevMessages[prevMessages.length - 1];
        if (lastMessage && lastMessage.sender === 'bot') {
          return [
            ...prevMessages.slice(0, -1), // enfernt letzte element des Arrays
            { ...lastMessage, complete: true, time: data.time, model : modelRef.current } // Antwort als vollständig markieren
          ];
        }
        return prevMessages;
      });
    });
    socket.on('error', (error) => {
      console.error('Error:', error);
    });

    return () => {
      // Cleanup: Events entfernen
      socket.off('response');
      socket.off('error');
    };
  }, []);

  // Scrollen bei jeder Änderung von messages
  useEffect(() => {
    scrollToBottom();
    console.log(messages);
  }, [messages]);

  // User Nachricht absenden
  // useCallback ist ein React-Hook, der eine memoisierte Version der Funktion zurückgibt. 
  // Das bedeutet, dass die Funktion nur dann neu erstellt wird, wenn eine ihrer Abhängigkeiten sich geändert hat. 
  // Andernfalls gibt useCallback die alte Referenz der Funktion zurück, was bedeutet, dass die Funktion stabil bleibt und nicht bei jedem Render neu erstellt wird.
  const sendMessage = useCallback(() => {
    if (!userInput.text.trim() || userInput.value === "0") {
      return;
    }
    // User-Nachricht in den State
    setMessages((prevMessages) => {
      const newMessages = [...prevMessages, { sender: 'user', text: userInput.text.trim() }];
      return newMessages;
    });
  
    // An den Server via Socket.IO
    socket.emit('message', { text: userInput.text.trim(), model: Model });
  
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
    localStorage.setItem("selectedModel", selectedModel); // Speichern für Neuladen
  };
  return (
      <header className="App-header">
        <div className ="dropdown-container model">
          <select id="options" value = {Model} onChange = {handelevent}>
              <option value="Lama 3.1">Lama 3.1</option>
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
        </div>
      </header>
  );
}

export default ChatPage;