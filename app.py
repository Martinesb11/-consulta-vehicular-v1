from flask import Flask, request, jsonify
from datetime import datetime
import json

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        raw_data = request.get_data(as_text=True)
        json_data = request.get_json(silent=True) or {}

        print("\n====================================", flush=True)
        print(f"🕒 {ahora}", flush=True)
        print("📥 RAW BODY:", raw_data, flush=True)
        print("📦 JSON COMPLETO:", json.dumps(json_data, ensure_ascii=False, indent=2), flush=True)

        # UltraMsg a veces manda la info dentro de "data"
        msg_data = json_data.get('data', json_data)

        chat_id = (
            msg_data.get('from')
            or msg_data.get('chatId')
            or msg_data.get('to')
            or json_data.get('from')
            or json_data.get('chatId')
        )

        autor = (
            msg_data.get('author')
            or msg_data.get('participant')
            or json_data.get('author')
        )

        body = (
            msg_data.get('body')
            or msg_data.get('text')
            or json_data.get('body')
        )

        print(f"📌 ID DETECTADO: {chat_id}", flush=True)
        print(f"👤 AUTOR: {autor}", flush=True)
        print(f"💬 MENSAJE: {body}", flush=True)

        if chat_id:
            if str(chat_id).endswith("@g.us"):
                print("🔥 TIPO: GRUPO DE WHATSAPP", flush=True)
            elif str(chat_id).endswith("@c.us"):
                print("📱 TIPO: CHAT PERSONAL", flush=True)
            else:
                print("❓ TIPO: DESCONOCIDO", flush=True)
        else:
            print("⚠️ No se encontró chat_id en el payload", flush=True)

        print("====================================\n", flush=True)

        return jsonify({
            'status': 'ok',
            'chat_id_detectado': chat_id,
            'autor': autor,
            'mensaje': body
        }), 200

    except Exception as e:
        print(f"❌ ERROR EN WEBHOOK: {e}", flush=True)
        return jsonify({'status': 'error', 'detalle': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'modo': 'detector_grupo_activo'
    }), 200


if __name__ == '__main__':
    print("🚀 MODO DETECCIÓN DE GRUPOS ACTIVADO", flush=True)
    print("📩 Envía un mensaje en el grupo para ver su ID en los logs", flush=True)
    app.run(host='0.0.0.0', port=8080, debug=False)
