# Beispiel-Dictionary
info = {
    "name": "Max Mustermann",
    "age": 30,
    "city": "Berlin"
}

# Zugriff direkt über eckige Klammern
# Wir erhalten den Wert für "name" oder einen KeyError, falls "name" nicht existiert
name = info["name"]
print("Name:", name)

# Zugriff mit .get()
# Gibt den Wert für "city" zurück oder None, wenn der Schlüssel nicht existiert
stadt = info.get("city")
print("Stadt:", stadt)

# Optionaler Standardwert mit .get()
# Gibt den Wert für "job" zurück oder, wenn es das Schlüsselwort nicht gibt,
# "unbekannt"
beruf = info.get("job", "unbekannt")
print("Beruf:", beruf)