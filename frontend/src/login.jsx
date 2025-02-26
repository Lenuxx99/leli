import React, { useState } from "react";

import './login.css';
function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [responseMsg, setResponseMsg] = useState("");

  const handleSubmit = async (event) => {
    event.preventDefault();

    try {
      // API-Aufruf an Flask
      const resp = await fetch("api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });

      const data = await resp.json();

      if (resp.ok) {
        // Login war erfolgreich
        setResponseMsg("Login erfolgreich: " + data.message);
        // evtl. Navigation auf eine andere Seite
      } else {
        // Login fehlgeschlagen
        setResponseMsg("Fehler: " + data.message);
      }
    } catch (error) {
      setResponseMsg("Netzwerk- oder Serverfehler!");
      console.error(error);
    }
  };

  return (
    <div className = "container">
      <h2>Login</h2>
      <form onSubmit={handleSubmit}>
        <div>
          <label>Username:</label><br />
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>
        <div>
          <label>Password:</label><br />
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        <button type="submit" style={{marginTop: '1rem'}}>Login</button>
      </form>

      {responseMsg && <p>{responseMsg}</p>}
    </div>
  );
}

export default Login;