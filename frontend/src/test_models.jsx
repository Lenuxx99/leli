import React, { useState } from "react";
import "./test_models.css";
import JSZip from "jszip";

function TestModels({ selectedFile }) {
    const handelclick = async () => {
        const button = document.getElementById("testModels");
        const originalText = button.innerHTML;

        button.disabled = true;
        button.innerHTML = `Wird geladen...<span class="loader"></span>`;
        try {
            if (!selectedFile) {
                alert("Bitte wählen Sie eine PDF aus.");
                return;
            }
            const request = await fetch("http://localhost:5000/api/testmodel", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ file: selectedFile })
            });

            if (!request.ok) {
                throw new Error(`Fehler beim server request: ${request.statusText}`);
            }
            
            const response = await request.json()

            if (!Array.isArray(response.results) || response.results.length === 0) {
                throw new Error("Ungültige oder leere Antwort vom Server.");
            }

            console.log(response)
            downloadCSVandJSON(response)
        } catch (error) {
            console.error("Fehler beim testen:", error);
            alert("Testen fehlgeschlagen!");
        } finally {
            button.disabled = false;
            button.innerHTML = originalText;
        }
    }
    return (
        <button
            id="testModels"
            className="testModels"
            onClick={handelclick}
        >
            test Models</button>
    );
}

const downloadCSVandJSON = async (data) => {
    if (!data.questions || !data.results) {
        alert("Fehler: Ungültige Serverantwort.");
        return;
    }

    const zip = new JSZip();

    // CSV-Datei generieren
    let headers = ["Model"];
    data.questions.forEach(question => {
        headers.push(`${question} - Antwortszeit in s`);
    });

    const csvContent = data.results.map(row => row.join(",")).join("\n");
    const csvString = headers.join(",") + "\n" + csvContent;

    // ✅ CSV-Datei hinzufügen
    zip.file("test_results.csv", csvString);

    // ✅ JSON-Datei hinzufügen
    const jsonString = JSON.stringify(data.allInfos, null, 2);
    zip.file("test_results.json", jsonString);

    // 🔽 ZIP generieren und als Datei speichern
    const zipBlob = await zip.generateAsync({ type: "blob" });
    const zipUrl = URL.createObjectURL(zipBlob);
    const zipLink = document.createElement("a");
    zipLink.href = zipUrl;
    zipLink.download = "test_results.zip";
    document.body.appendChild(zipLink);
    zipLink.click();
    document.body.removeChild(zipLink);
};;

export default TestModels