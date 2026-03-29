import os
import requests
from flask import Flask, request, jsonify
from consulta import (
    consultar_ruc,
    consultar_vehiculo,
    consultar_imei,
    consultar_record_conductor,
    consultar_tipo_cambio
)

app = Flask(__name__)

# ─── Variables de entorno ────────────────────────────────────────────
ULTRAMSG_TOKEN    = os.environ.get("ULTRAMSG_TOKEN", "")
ULTRAMSG_INSTANCE = os.environ.get("ULTRAMSG_INSTANCE", "")
GRUPO_AUTORIZADO  = os.environ.get("GRUPO_AUTORIZADO", "")
CV_USUARIO        = os.environ.get("CV_USUARIO", "")
CV_CONTRASENA     = os.environ.get("CV_CONTRASENA", "")

print(f"🚀 Servidor iniciando en puerto 8080")
print(f"📍 Grupo autorizado: {GRUPO_AUTORIZADO}")

# ─── Enviar mensaje ──────────────────────────────────────────────────
def enviar_mensaje(chat_id: str, texto: str):
    url = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat"
    payload = {
        "token": ULTRAMSG_TOKEN,
        "to": chat_id,
        "body": texto
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print(f"📤 Mensaje enviado a {chat_id}: {r.status_code}")
    except Exception as e:
        print(f"❌ Error al enviar mensaje: {e}")

# ─── Webhook ─────────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return jsonify({"status": "ok"})

    msg_data = data.get("data", {})
    chat_id  = msg_data.get("from", "")
    body     = msg_data.get("body", "").strip()
    es_grupo = msg_data.get("isGroupMsg", False)

    # ── DEBUG: imprime SIEMPRE el origen del mensaje ──
    print(f"📨 Mensaje de: [{chat_id}] | Grupo: {es_grupo} | Texto: {body}")

    # ── Ignorar mensajes propios del bot ──
    if msg_data.get("fromMe", False):
        return jsonify({"status": "ok"})

    # ── Filtro: solo responder al grupo autorizado ──
    if GRUPO_AUTORIZADO and chat_id != GRUPO_AUTORIZADO:
        print(f"⛔ Mensaje ignorado. Origen: {chat_id} | Esperado: {GRUPO_AUTORIZADO}")
        return jsonify({"status": "ignorado"})

    # ── Procesar comandos ──
    texto_lower = body.lower()

    # /ruc
    if texto_lower.startswith("/ruc"):
        partes = body.split()
        if len(partes) < 2:
            enviar_mensaje(chat_id, "⚠️ Uso correcto: /ruc 20123456789")
        else:
            ruc = partes[1].strip()
            enviar_mensaje(chat_id, f"🔍 Consultando RUC {ruc}...")
            resultado = consultar_ruc(ruc)
            enviar_mensaje(chat_id, resultado)

    # /vehiculo
    elif texto_lower.startswith("/vehiculo"):
        partes = body.split()
        if len(partes) < 2:
            enviar_mensaje(chat_id, "⚠️ Uso correcto: /vehiculo ABC123")
        else:
            placa = partes[1].strip().upper()
            enviar_mensaje(chat_id, f"🔍 Consultando placa {placa}...")
            resultado = consultar_vehiculo(placa, CV_USUARIO, CV_CONTRASENA)
            enviar_mensaje(chat_id, resultado)

    # /imei
    elif texto_lower.startswith("/imei"):
        partes = body.split()
        if len(partes) < 2:
            enviar_mensaje(chat_id, "⚠️ Uso correcto: /imei 359123456789012")
        else:
            imei = partes[1].strip()
            enviar_mensaje(chat_id, f"🔍 Consultando IMEI {imei}...")
            resultado = consultar_imei(imei)
            enviar_mensaje(chat_id, resultado)

    # /record
    elif texto_lower.startswith("/record"):
        partes = body.split()
        if len(partes) < 2:
            enviar_mensaje(chat_id, "⚠️ Uso correcto: /record 12345678")
        else:
            licencia = partes[1].strip()
            enviar_mensaje(chat_id, f"🔍 Consultando récord de licencia {licencia}...")
            resultado = consultar_record_conductor(licencia)
            enviar_mensaje(chat_id, resultado)

    # /cambio
    elif texto_lower.startswith("/cambio"):
        enviar_mensaje(chat_id, "🔍 Consultando tipo de cambio...")
        resultado = consultar_tipo_cambio()
        enviar_mensaje(chat_id, resultado)

    # /ayuda
    elif texto_lower in ["/ayuda", "/help", "/start"]:
        ayuda = (
            "🤖 *Bot de Consultas* — Comandos disponibles:\n\n"
            "📋 */ruc* 20123456789 — Consulta RUC en SUNAT\n"
            "🚗 */vehiculo* ABC123 — Consulta placa vehicular\n"
            "📱 */imei* 359123456789012 — Verifica IMEI\n"
            "🪪 */record* 12345678 — Récord de conductor\n"
            "💱 */cambio* — Tipo de cambio del día\n"
            "❓ */ayuda* — Muestra este menú"
        )
        enviar_mensaje(chat_id, ayuda)

    else:
        # Mensaje no reconocido — no responder para no ser spam
        print(f"ℹ️ Comando no reconocido: {body}")

    return jsonify({"status": "ok"})

# ─── Health check ────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "running", "grupo": GRUPO_AUTORIZADO})

# ─── Main ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
