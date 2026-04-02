from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json or {}
    msg_data = data.get('data', {})

    chat_id = msg_data.get('from')
    autor = msg_data.get('author')
    body = msg_data.get('body')

    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print("\n====================================")
    print(f"🕒 {ahora}")
    print(f"📌 ID DEL CHAT: {chat_id}")
    print(f"👤 AUTOR: {autor}")
    print(f"💬 MENSAJE: {body}")

    # Detectar tipo de chat
    if chat_id:
        if chat_id.endswith("@g.us"):
            print("🔥 TIPO: GRUPO DE WHATSAPP")
        elif chat_id.endswith("@c.us"):
            print("📱 TIPO: CHAT PERSONAL")
        else:
            print("❓ TIPO: DESCONOCIDO")

    print("====================================\n")

    return jsonify({'status': 'ok'}), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'modo': 'detector_grupo_activo'
    }), 200


if __name__ == '__main__':
    print("🚀 MODO DETECCIÓN DE GRUPOS ACTIVADO")
    print("📩 Envía un mensaje en el grupo para ver su ID en los logs")
    app.run(host='0.0.0.0', port=8080)
