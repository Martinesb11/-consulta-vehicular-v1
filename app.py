import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

ULTRAMSG_INSTANCE = os.environ.get('ULTRAMSG_INSTANCE', '')
ULTRAMSG_TOKEN = os.environ.get('ULTRAMSG_TOKEN', '')
GRUPO_AUTORIZADO = os.environ.get('GRUPO_AUTORIZADO', '120363423872611684@g.us')

def enviar_mensaje(destino, texto):
    try:
        url = f'https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat'
        payload = {
            'token': ULTRAMSG_TOKEN,
            'to': destino,
            'body': texto
        }

        print(f'📤 URL: {url}', flush=True)
        print(f'📤 PAYLOAD: {payload}', flush=True)

        r = requests.post(url, data=payload, timeout=30)

        print(f'📩 STATUS: {r.status_code}', flush=True)
        print(f'📩 RESPUESTA: {r.text}', flush=True)

        return r.status_code in [200, 201]
    except Exception as e:
        print(f'❌ ERROR enviando mensaje: {e}', flush=True)
        return False

@app.route('/webhook', methods=['POST'])
def webhook():
    print('🔥 WEBHOOK ACTIVADO', flush=True)

    data = request.get_json(silent=True) or {}
    print(f'📥 JSON: {data}', flush=True)

    ok = enviar_mensaje(GRUPO_AUTORIZADO, '🚀 prueba desde webhook')
    print(f'✅ RESULTADO ENVIO: {ok}', flush=True)

    return jsonify({'status': 'ok', 'envio': ok}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print('🚀 APP DE PRUEBA DE SALIDA INICIADA', flush=True)
    app.run(host='0.0.0.0', port=port, debug=False)
