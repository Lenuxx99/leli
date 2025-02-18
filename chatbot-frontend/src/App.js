import React from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Chat from "./ChatPage";
import Login from "./Login";   
import './App.css';

function App() {
  return (
    <BrowserRouter>
      <div className="App">
       
          {/* Navigation oben rechts */}
          {/* <header>
            <div className="top-nav">
              <Link to="/login">Login</Link>
              <Link to="/signup">Sign Up</Link>
            </div>
          </header> */}

          {/* Routen definieren */}
          {/* Routen in React lassen (Single-Page Application)
          Hier sind die Routen für ChatPage, Login, Signup usw. vollständig clientseitig in React. 
          Dadurch bleibt die App eine Single-Page Application (SPA). 
          Die Navigation ist schnell und erfolgt ohne Neuladen der Seite. 
          Flask dient in diesem Szenario nur als API-Server. Daher es handelt sich um Cross-Origin-Anfragen. Deshalb muss das Flask-Backend CORS erlauben */}
          <Routes>
            {/* Standard-/Start-Seite führt zum Chat */}
            <Route path="/" element={<Chat />} />

            {/* /login-Seite */}
            <Route path="/login" element={<Login />} />

            {/* /signup-Seite (noch zu erstellen) */}
            {/* <Route path="/signup" element={<Signup />} /> */}
          </Routes>
        
      </div>
    </BrowserRouter>
  );
}

export default App;