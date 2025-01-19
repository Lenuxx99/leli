from flask import Flask, request
from flask_socketio import SocketIO, emit
import requests
import json

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # Aktiviert CORS für Socket.IO

@socketio.on('message')
def handle_message(data):
    try:
        user_input = data['text']  # Eingabedaten des Clients
        url = "http://localhost:11434/api/chat"
        payload = {
            "model": "llama3.1:8b",
            "messages": [{"role": "user", "content": user_input}]
        }

        # Anfrage an den Chatbot senden (Streaming)
        response = requests.post(url, json=payload, stream=True)
        if response.status_code == 200:
            # Antwort in Echtzeit senden
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    json_data = json.loads(line)
                    if "message" in json_data and "content" in json_data["message"]:
                        emit('response', {'response': json_data["message"]["content"]})
        else:
            emit('error', {'error': 'Failed to connect to the chat model'})
    except Exception as e:
        app.logger.error(f'Error processing request: {str(e)}')
        emit('error', {'error': 'Internal Server Error'})

if __name__ == '__main__':
    socketio.run(app, debug=True)







# @socketio.on('event_one')
# def handle_event_one(data):
#     print("Data for event_one:", data)

# @socketio.on('event_two')
# def handle_event_two(data):
#     print("Data for event_two:", data)