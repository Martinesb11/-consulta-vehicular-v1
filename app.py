import os
from flask import Flask, request

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data:
        from_id = data.get('from', 'desconocido')
        body    = data.get('body', '')
        tipo    = data.get('type', '')
        print(f"📌 ID: {from_id} | TIPO: {tipo} | MENSAJE: {body[:40]}")
    return 'OK', 200

@app.route('/', methods=['GET'])
def health():
    return 'Bot activo ✅', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
