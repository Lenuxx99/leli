import React, { useState, useEffect } from "react";
import "../styles/Sidebar.css";

function Sidebar({ selectedFile, setSelectedFile, Model, serverconnected }) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [pdfFiles, setPdfFiles] = useState(() => {
    const storedPdfs = localStorage.getItem("pdfs");
    return storedPdfs ? JSON.parse(storedPdfs) : [];
  });

  useEffect(() => {
    const handleClickOutsideSidebar = (event) => {
      if (!event.target.closest("#sidebar") && isCollapsed) {
        setTimeout(() => setIsCollapsed(false), 100); // Verzögert das Schließen um 100ms
      }
    };
  
    document.addEventListener("click", handleClickOutsideSidebar);
  
    return () => {
      document.removeEventListener("click", handleClickOutsideSidebar);
    };
  }, [isCollapsed]);
  
  const handleFileSelect = async (event) => {
    // holt die ausgewählte PDFs
    const files = Array.from(event.target.files);
    const pdfFiles = files.filter(file => file.type === "application/pdf");
    if (pdfFiles.length === 0) {
      alert("Bitte nur PDF-Dateien hochladen.");
      return;
    }

    const storedFiles = JSON.parse(localStorage.getItem("pdfs")) || [];

    const newFiles = pdfFiles.filter(file => !storedFiles.some(storedFile => storedFile.name === file.name));

    if (newFiles.length === 0) {
      alert("Diese Datei(en) wurden bereits hochgeladen.");
      return;
    }
    // FormData-Typ
    // Typ: FormData (eine spezielle Klasse im Browser)
    // Struktur: Enthält Key-Value-Paare, wobei der Key ein String und der Wert entweder ein String oder eine Datei ist.
    // Mehrere Werte pro Key: Ein Key kann mehrere Werte haben (z. B. mehrere Dateien mit dem gleichen Key).
    // Dateien in FormData umwandeln für den Server

    // Erstellt ein FormData-Objekt, das verwendet wird, um Formulardaten (einschließlich Dateien) zu speichern und an den Server zu senden (Dateien wie Bilder und PDFs können nicht in json form umgewandelt).
    const formData = new FormData();
    newFiles.forEach(file => formData.append("AllPdfs", file));

    try {
      const response = await fetch("http://localhost:5000/api/embedding", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Fehler beim Upload: ${response.statusText}`);
      }

      const result = await response.json();
      console.log("Upload erfolgreich:", result);

      setPdfFiles((prevFiles) => {
        const allFiles = [...prevFiles, ...result.files];
        localStorage.setItem("pdfs", JSON.stringify(allFiles));
        return allFiles;
      });
      if (result.error.length > 0) {
        alert(result.error.split(",").join("\n") + "\nwurden nicht richtig gelesen, daher sind sie nicht beigefügt.");
      }
    } catch (error) {
      console.error("Fehler:", error);
      alert("Upload fehlgeschlagen!");
      return;
    }
  };

  const deleteFile = async (index) => {
    const fileToDelete = pdfFiles[index];
    console.log("Lösche Datei mit Index:", index);
    const newFiles = pdfFiles.filter((_, i) => i !== index);
    setPdfFiles(newFiles);
    localStorage.setItem("pdfs", JSON.stringify(newFiles));

    try {
      const response = await fetch(`http://localhost:5000/api/delete_embedding`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ filename: fileToDelete.name }), // Datei an den Server senden
      });

      if (!response.ok) {
        throw new Error(`Fehler beim Löschen: ${response.statusText}`);
      }

      console.log(`Datei ${fileToDelete.name} erfolgreich gelöscht`);
    } catch (error) {
      console.error("Fehler beim Löschen:", error);
      alert("Löschen fehlgeschlagen!");
    }
  };

  const createJson = async () => {
    const button = document.getElementById("createjson"); //DOM direkt Manipulieren, keine useState ist nötig
    const originalText = button.innerHTML;

    button.disabled = true;
    button.innerHTML = `Wird geladen...<span class="loader"></span>`;
    try {
      const response = await fetch("http://localhost:5000/api/getjson", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ model: Model }),
      });

      const results = await response.json();

      // Prüfen, ob results ein Array ist und model hinzufügen
      if (Array.isArray(results)) {
        results.forEach((result) => result.model = Model);
      } else if (typeof results === "object" && results !== null) {
        results.model = Model;
      }

      // JSON direkt senden → Wenn du nur Textdaten hast.
      // Blob für JSON nutzen → Falls du JSON als Datei speichern oder mit FormData kombinieren musst.
      // FormData nutzen → Wenn du Dateien (PDF, Bilder, Videos) an den Server senden willst.
      // JSON als Blob erstellen
      const blob = new Blob([JSON.stringify(results, null, 2)], { type: "application/json" });

      // Download-Link erstellen
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = "data.json";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error("Fehler beim Abrufen der JSON-Daten:", error);
      alert("Fehler beim Abrufen der JSON-Daten.\nMöglicher Grund: Server ist nicht gestartet.");
    } finally {
      button.disabled = false;
      button.innerHTML = originalText;
    }
  };
  return (
    <div className={`sidebar ${isCollapsed ? "collapsed" : ""}`} id = "sidebar">
      <button className="toggle-btn" onClick={() => setIsCollapsed(!isCollapsed)}>
        {isCollapsed ? "➤" : "◄"}
      </button>
      <div className="sidebar_header">
        <button
          className="add-button"
          onClick={() => document.getElementById("fileInput").click()}
          style={{
            display: isCollapsed ? "block" : "none",
            padding: "10px 15px",
            backgroundColor: "#4CAF50",
            color: "white",
            border: "none",
            borderRadius: "5px",
            cursor: "pointer",
            fontSize: "0.8rem",
          }}
        >
          + PDF hinzufügen
        </button>
      </div>
      <div className="sidebar_body" style={{ display: isCollapsed ? "block" : "none" }}>
        {pdfFiles.map((file, index) => (
          <div className="pdfs" key={index}>
            <input
              type="radio"
              name="selectedPDF"
              checked={selectedFile === file.name}
              onChange={() => setSelectedFile(file.name)}
              style={{ cursor: "pointer", marginBottom: "2px" }}
            />
            <img src="./pdf-icon.png" alt="PDF" className="pdf-icon" />
            <p
              title={file.name}
              onClick={() => window.open(file.url, "_blank")}
              style={{ cursor: "pointer", color: "white", textDecoration: "none" }}
            >
              {file.name}
            </p>
            <button
              className="delete-btn"
              disabled={!serverconnected}
              title={!serverconnected ? "Server nicht aktiv" : "Löschen"}
              onClick={(event) => {
                if (!serverconnected) return;
                event.stopPropagation();
                deleteFile(index);
              }}
            >
              ❌
            </button>
          </div>
        ))}

        <input
          id="fileInput"
          type="file"
          multiple
          accept="application/pdf"
          style={{ display: "none" }}
          onChange={handleFileSelect}
        />
      </div>
      <div className="sidebar-footer" style={{ textAlign: "center", marginTop: "20px", display: isCollapsed ? "flex" : "none", width: "100%", justifyContent: "center", position: "relative" }}>
        {pdfFiles.length > 0 &&
          <button style={{
          padding: "10px 15px",
          backgroundColor: "#34495e",
          color: "white",
          border: "none",
          borderRadius: "5px",
          cursor: "pointer",
          fontSize: "0.8rem",
          display: "flex",
          justifyContent: "center",
          textAlign: "center",
          gap: "8px",
          alignItems: "center"
        }} onClick={(event) => {
          event.stopPropagation(); // Verhindert das Auslösen des globalen Klick-Handlers
          createJson();
        }}
        id="createjson">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="white" viewBox="0 0 16 16">
            <path d="M.5 9.9V13a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V9.9a.5.5 0 0 0-1 0V13a1 1 0 0 1-1 1H2.5a1 1 0 0 1-1-1V9.9a.5.5 0 0 0-1 0ZM7.5 1v7.293L5.354 6.146a.5.5 0 1 0-.708.708l3 3a.5.5 0 0 0 .708 0l3-3a.5.5 0 1 0-.708-.708L8.5 8.293V1a.5.5 0 0 0-1 0Z" />
          </svg>
          <span>JSON aus PDFs generieren</span>
        </button>}
        <div className = "hide_info">Request Timeout erfolgt 40s nach dem Start.</div>
      </div>
    </div>
  );
}
export default Sidebar;