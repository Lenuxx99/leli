from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json

app = Flask(__name__)
CORS(app)  # Aktiviert CORS für alle Domains und Routen


@app.route('/', methods=['POST'])
def ask():
    
    try:
        user_input = request.json['text']
        url = "http://localhost:11434/api/chat"
        payload = {
            "model": "llama3.1:8b",
            "messages": [{"role": "user", "content": user_input}]
        }
        response = requests.post(url, json=payload, stream=True)
        print(user_input)
        if response.status_code == 200:
            content = ""
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    json_data = json.loads(line)
                    if "message" in json_data and "content" in json_data["message"]:
                        content += json_data["message"]["content"]
            return jsonify({'response': content})
        else:
            return jsonify({'error': 'Failed to connect to the chat model'}), 500
    except Exception as e:
        app.logger.error(f'Error processing request: {str(e)}')
        return jsonify({'error': 'Internal Server Error'}), 500

if __name__ == '__main__':
    app.run(debug=True)


