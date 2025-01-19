import React, { useState, useEffect, useRef } from 'react';
import { io } from 'socket.io-client';
import './App.css';

const socket = io('http://localhost:5000');

function App() {
  const [userInput, setUserInput] = useState('');
  const [messages, setMessages] = useState([]); // State für alle Nachrichten
  const messagesEndRef = useRef(null); // Ref für den unteren Bereich der Nachrichtenliste

  // Funktion zum automatischen Scrollen
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  useEffect(() => {
    scrollToBottom();
    socket.on('response', (data) => {
      // setMessages(() => {
      //   return [{ sender: 'bot', text: data.response + ' ', complete: false }];
      // });
      // oder
      // setMessages([{ sender: 'bot', text: data.response + ' ', complete: false }]);
      // setz den Array auf dieser angegeben objekt


      // setMessages((prev) => {[
      //   ...prev,
      //   { sender: 'bot', text: data.response + ' ', complete: false }
      // ]});
      // fügt die neue objekt zur vorherigen objekten, prev ist einen array der vorherigen nachrichten


      // cont  [count ,setCount] = useState({number : 2})
      // prev in diesem fall ist ein JavaScript-Objekt enthält alle numbers
      // setCount ((prev) => {
      //   const neu = prev.number * prev.number;
      //   return {
      //     ...prev,
      //     number : neu
      //   }
      // });
      // Der Anfangswert number: 2 wird quadriert (2 → 4 → 16 → 256 usw.).


      // cont  [count ,setCount] = useState(0)
      // setCount (prev => prev + 1);
      // setCount ((prev) => {
      //   const add = prev + 1;
      //   return add
      // });
      // count wird jedes mal um eins erhöht

      // const jsonString = JSON.stringify({ number: 2 }); // Erzeugt einen JSON-String
      // const lal = JSON.parse(jsonString); // Wandelt den JSON-String zurück in ein Objekt
      // console.log(lal); // { number: 2 }


      // die nutzung von usestate dient dazu dass jede änderung von der gezielt variable wird auf der UI aktualisiert
      // Normale variablen, die auf der UI gezeigt werden müssen, werden bei ihre änderung auf der UI aktualisiert
      setMessages((prevMessages) => {                                               // callback funtktion und die parameter pervMessages bereibt gegeben, für callback funtkion die die parameter nicht expliziet in körper der callbackfunktion genutzt werden kann hier nicht gegeben wird 
        const lastMessage = prevMessages[prevMessages.length - 1];
        // Aktualisiere die letzte Bot-Nachricht, falls sie noch nicht abgeschlossen ist
        if (lastMessage && lastMessage.sender === 'bot' && !lastMessage.complete) {
          return [
            ...prevMessages.slice(0, -1),
            { ...lastMessage, text: (lastMessage.text + data.response + ' ')},
          ];
        }
        // Falls keine unfertige Bot-Nachricht existiert, füge eine neue hinzu
        return [...prevMessages, { sender: 'bot', text: (data.response + ' '), complete: false }];
      });
    });

    socket.on('response_end', () => {
      // Markiere die letzte Bot-Nachricht als abgeschlossen
      setMessages((prevMessages) => {
        const lastMessage = prevMessages[prevMessages.length - 1];
        if (lastMessage && lastMessage.sender === 'bot' && !lastMessage.complete) {
          return [
            ...prevMessages.slice(0, -1),
            { ...lastMessage, text: lastMessage.text.trim(), complete: true },
          ];
        }
        return prevMessages;
      });
    });

    socket.on('error', (error) => {
      console.error('Error:', error);
    });

    return () => {                      // k tetbadel wahda m dependecies hethy besh tetausführa a baad tarjaa lfou9 tausführi lhook
      socket.off('response');
      socket.off('response_end');
      socket.off('error');
    };
  }, [messages]);

  const sendMessage = () => {
    if (userInput.trim() === '') {
      // Fokus auf das Eingabefeld setzen, wenn die Eingabe leer ist
      document.querySelector('input').focus();
      return; // Beendet die Funktion
    }

    // Nachricht des Benutzers zur Nachrichtenliste hinzufügen
    setMessages((prevMessages) => [
      ...prevMessages,
      { sender: 'user', text: userInput.trim() },
    ]);

    // Nachricht an den Server senden
    socket.emit('message', { text: userInput.trim() });

    // Eingabefeld zurücksetzen
    setUserInput('');
  };
  
  return (
    <div className="App">
      <header className="App-header">
        <h1>Chat with Our Bot</h1>
        <div className="formular">
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            placeholder="Type your message..."
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                sendMessage(); // Sendet die Nachricht
              }
            }}
          />
          <button onClick={() => sendMessage()}>Send</button>
        </div>

        <div className="response-list">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`response-container ${msg.sender === 'user' ? 'user-message' : 'bot-message'
                }`}
            >
              <p
                className="response"
                dangerouslySetInnerHTML={{
                  __html: msg.text
                    .replace(/\n/g, '<br>') // Beibehaltung von Zeilenumbrüchen
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'), // Markdown zu HTML
                }}
              ></p>
            </div>
          ))}
          <div ref={messagesEndRef}></div>
        </div>
      </header>
    </div>
  );
}

export default App;
