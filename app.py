import os
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

GRUPO_AUTORIZADO = os.environ.get('GRUPO_AUTORIZADO', '120363423872611684@g.us')

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        raw = request.get_data(as_text=True)
        data = request.get_json(silent=True) or {}

        print("\n================ WEBHOOK ================", flush=True)
        print("RAW:", raw, flush=True)
        print("JSON:", json.dumps(data, ensure_ascii=False, indent=2), flush=True)

        msg_data = data.get('data', data)

        from_id = msg_data.get('from')
        from_me = msg_data.get('fromMe')
        body = msg_data.get('body')
        author = msg_data.get('author')

        print(f"GRUPO_AUTORIZADO={GRUPO_AUTORIZADO}", flush=True)
        print(f"from={from_id}", flush=True)
        print(f"fromMe={from_me}", flush=True)
        print(f"author={author}", flush=True)
        print(f"body={body}", flush=True)

        if from_id != GRUPO_AUTORIZADO:
            print("🚫 Ignorado: grupo no coincide", flush=True)
            return jsonify({
                'status': 'ignorado',
                'motivo': 'grupo_no_coincide',
                'from': from_id,
                'grupo_autorizado': GRUPO_AUTORIZADO
            }), 200

        if from_me:
            print("🚫 Ignorado: mensaje propio", flush=True)
            return jsonify({'status': 'ignorado', 'motivo': 'fromMe'}), 200

        if not body:
            print("🚫 Ignorado: body vacío", flush=True)
            return jsonify({'status': 'ignorado', 'motivo': 'body_vacio'}), 200

        body_up = body.strip().upper()
        print(f"✅ body_up={body_up}", flush=True)

        if not body_up.startswith('CONSULTA '):
            print("🚫 Ignorado: no empieza con CONSULTA", flush=True)
            return jsonify({
                'status': 'ignorado',
                'motivo': 'comando_no_valido',
                'body_up': body_up
            }), 200

        print("🔥 El flujo sí está entrando correctamente", flush=True)
        return jsonify({'status': 'ok', 'mensaje': 'flujo correcto'}), 200

    except Exception as e:
        print(f"❌ ERROR EN WEBHOOK: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'detalle': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'grupo_autorizado': GRUPO_AUTORIZADO
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f'🚀 Servidor iniciando en puerto {port}', flush=True)
    print(f'📍 Grupo autorizado: {GRUPO_AUTORIZADO}', flush=True)
    app.run(host='0.0.0.0', port=port, debug=False)
