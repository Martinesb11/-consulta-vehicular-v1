import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ── Variables de entorno ─────────────────────────────────
ULTRAMSG_TOKEN    = os.environ.get("ULTRAMSG_TOKEN", "")
ULTRAMSG_INSTANCE = os.environ.get("ULTRAMSG_INSTANCE", "")
NUMEROS_AUTORIZADOS = os.environ.get("NUMEROS_AUTORIZADOS", "")

print(f"🚀 Servidor iniciando en puerto 8080")
print(f"📍 Número/Grupo autorizado: {NUMEROS_AUTORIZADOS}")

# ── Enviar mensaje ───────────────────────────────────────
def enviar_mensaje(numero, mensaje):
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat"
    payload = {
        "token": ULTRAMSG_TOKEN,
        "to": numero,
        "body": mensaje
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"📤 Enviado a {numero}: {r.status_code}")
    except Exception as e:
        print(f"❌ Error al enviar: {e}")

# ── Webhook ──────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return jsonify({"status": "ok"})

    msg_data  = data.get("data", {})
    from_     = msg_data.get("from", "")
    body      = msg_data.get("body", "").strip()
    es_grupo  = msg_data.get("isGroupMsg", False)

    # ── DEBUG: captura el ID del grupo ───────────────────
    print(f"📨 from=[{from_}] | grupo={es_grupo} | texto={body}")

    # Ignorar mensajes propios
    if msg_data.get("fromMe", False):
        return jsonify({"status": "ok"})

    # Responder para confirmar que el bot está activo
    enviar_mensaje(from_, "🤖 Bot activo. El ID de este chat ya aparece en los logs de Railway.")

    return jsonify({"status": "ok"})

# ── Health check ─────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "running", "autorizado": NUMEROS_AUTORIZADOS})

# ── Main ─────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
