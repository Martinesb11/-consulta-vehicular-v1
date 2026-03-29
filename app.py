import os
import requests
from flask import Flask, request, jsonify
from consulta import consultar_vehiculo

app = Flask(__name__)

ULTRAMSG_TOKEN    = os.environ.get("ULTRAMSG_TOKEN", "")
ULTRAMSG_INSTANCE = os.environ.get("ULTRAMSG_INSTANCE", "")
GRUPO_AUTORIZADO  = os.environ.get("GRUPO_AUTORIZADO", "")
CV_USUARIO        = os.environ.get("CV_USUARIO", "")
CV_CONTRASENA     = os.environ.get("CV_CONTRASENA", "")

print(f"🚀 Servidor iniciando en puerto 8080")
print(f"📍 Grupo autorizado: {GRUPO_AUTORIZADO}")

def enviar_mensaje(chat_id: str, texto: str):
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat"
    payload = {"token": ULTRAMSG_TOKEN, "to": chat_id, "body": texto}
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"📤 Enviado a {chat_id}: {r.status_code}")
    except Exception as e:
        print(f"❌ Error al enviar: {e}")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return jsonify({"status": "ok"})

    msg_data = data.get("data", {})
    chat_id  = msg_data.get("from", "")
    body     = msg_data.get("body", "").strip()
    es_grupo = msg_data.get("isGroupMsg", False)

    # ── DEBUG: muestra el ID de donde venga el mensaje ──
    print(f"📨 Mensaje de: [{chat_id}] | Grupo: {es_grupo} | Texto: {body}")

    if msg_data.get("fromMe", False):
        return jsonify({"status": "ok"})

    # ── Filtro de grupo autorizado ──
    if GRUPO_AUTORIZADO and chat_id != GRUPO_AUTORIZADO:
        print(f"⛔ Ignorado. Origen: {chat_id} | Esperado: {GRUPO_AUTORIZADO}")
        return jsonify({"status": "ignorado"})

    # ── Comando /placa ──
    texto_lower = body.lower()
    if texto_lower.startswith("/placa"):
        partes = body.split()
        if len(partes) < 2:
            enviar_mensaje(chat_id, "⚠️ Uso: /placa ABC123")
        else:
            placa = partes[1].strip().upper()
            enviar_mensaje(chat_id, f"🔍 Consultando placa {placa}...")
            resultado = consultar_vehiculo(placa, CV_USUARIO, CV_CONTRASENA)
            enviar_mensaje(chat_id, resultado)

    elif texto_lower in ["/ayuda", "/help"]:
        enviar_mensaje(chat_id, "🚗 *Bot de Placas*\n\n*/placa* ABC123 — Consulta vehículo\n*/ayuda* — Muestra este menú")

    return jsonify({"status": "ok"})

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "running", "grupo": GRUPO_AUTORIZADO})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
