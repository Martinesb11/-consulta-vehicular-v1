import os
import time
import base64
import queue
import random
import threading
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from consulta import ejecutar_consulta_completa

app = Flask(__name__)

# ── Configuración ──────────────────────────────────────────
USUARIO_CV        = os.environ.get('CV_USUARIO', '')
CONTRASENA_CV     = os.environ.get('CV_CONTRASENA', '')
ULTRAMSG_INSTANCE = os.environ.get('ULTRAMSG_INSTANCE', '')
ULTRAMSG_TOKEN    = os.environ.get('ULTRAMSG_TOKEN', '')
GRUPO_AUTORIZADO  = os.environ.get('GRUPO_AUTORIZADO', '120363423872611684@g.us')
LIMITE_DIARIO     = int(os.environ.get('LIMITE_DIARIO', '15'))

# Caché
CACHE_HORAS = int(os.environ.get('CACHE_HORAS', '24'))

# Pausa aleatoria entre una consulta y la siguiente
PAUSA_MIN_SEG = float(os.environ.get('PAUSA_MIN_SEG', '5'))
PAUSA_MAX_SEG = float(os.environ.get('PAUSA_MAX_SEG', '12'))

# ⚠️ ACTUALIZA CON TUS NÚMEROS
MIEMBROS = {
    '51982008561': 'Juan',
    '51935203969': 'Alf',
    # '51999999999': 'Nombre',
}

# ── Cola de consultas (1 a la vez) ─────────────────────────
cola = queue.Queue()

# placas activas = en cola o en proceso
placas_activas = set()
lock_placas = threading.Lock()

def placa_esta_activa(placa):
    with lock_placas:
        return placa in placas_activas

def activar_placa(placa):
    with lock_placas:
        placas_activas.add(placa)

def liberar_placa(placa):
    with lock_placas:
        placas_activas.discard(placa)

def worker():
    while True:
        placa, destino, autor = cola.get()
        try:
            procesar_consulta(placa, destino, autor)
        except Exception as e:
            print(f'❌ Error en worker con {placa}: {e}')
            try:
                enviar_mensaje(destino, f'❌ Error interno procesando *{placa}*.')
            except Exception:
                pass
        finally:
            liberar_placa(placa)
            cola.task_done()

            # pausa aleatoria para evitar patrón rígido entre consultas
            pausa = random.uniform(PAUSA_MIN_SEG, PAUSA_MAX_SEG)
            print(f'⏸️ Pausa entre consultas: {pausa:.2f}s')
            time.sleep(pausa)

hilo_worker = threading.Thread(target=worker, daemon=True)
hilo_worker.start()

# ── Límite diario por usuario ──────────────────────────────
# { 'numero': {'fecha': 'YYYY-MM-DD', 'count': N} }
contadores = {}
lock_contadores = threading.Lock()

def verificar_limite(numero):
    """Retorna True si puede consultar, False si alcanzó el límite"""
    hoy = datetime.now().strftime('%Y-%m-%d')
    with lock_contadores:
        datos = contadores.get(numero, {'fecha': hoy, 'count': 0})

        if datos['fecha'] != hoy:
            datos = {'fecha': hoy, 'count': 0}

        if datos['count'] >= LIMITE_DIARIO:
            return False

        datos['count'] += 1
        contadores[numero] = datos
        return True

def consultas_restantes(numero):
    hoy = datetime.now().strftime('%Y-%m-%d')
    with lock_contadores:
        datos = contadores.get(numero, {'fecha': hoy, 'count': 0})

        if datos['fecha'] != hoy:
            return LIMITE_DIARIO

        return max(0, LIMITE_DIARIO - datos['count'])

# ── Anti-duplicados (caché 24h) ────────────────────────────
# { 'PLACA': {'timestamp': float, 'pdf_b64': str, 'fecha': str} }
cache_pdfs = {}
lock_cache = threading.Lock()

def obtener_cache(placa):
    """Retorna datos de caché si existen y no expiraron, sino None"""
    with lock_cache:
        dato = cache_pdfs.get(placa)
        if not dato:
            return None

        horas_pasadas = (time.time() - dato['timestamp']) / 3600
        if horas_pasadas > CACHE_HORAS:
            del cache_pdfs[placa]
            return None

        return dato

def guardar_cache(placa, pdf_b64):
    with lock_cache:
        cache_pdfs[placa] = {
            'timestamp': time.time(),
            'pdf_b64': pdf_b64,
            'fecha': datetime.now().strftime('%d/%m/%Y %I:%M %p')
        }
        print(f'💾 Caché guardado para {placa}')

# ── Log de uso ─────────────────────────────────────────────
def registrar_log(numero, placa, resultado, segundos):
    nombre = MIEMBROS.get(numero, numero)
    ahora = datetime.now()
    linea = f"{ahora.strftime('%Y-%m-%d')},{ahora.strftime('%H:%M:%S')},{numero},{nombre},{placa},{resultado},{segundos}\n"
    try:
        with open('log_consultas.csv', 'a', encoding='utf-8') as f:
            f.write(linea)
        print(f'📊 Log: {nombre} | {placa} | {resultado} | {segundos}s')
    except Exception as e:
        print(f'❌ Error en log: {e}')

# ── Utilidades ─────────────────────────────────────────────
def normalizar_placa(texto):
    return ''.join(ch for ch in (texto or '').upper().strip() if ch.isalnum())

def placa_valida(placa):
    return 6 <= len(placa) <= 8

def extraer_numero_autor(msg_data):
    return (
        (msg_data.get('author') or msg_data.get('from', ''))
        .replace('@c.us', '')
        .replace('+', '')
        .strip()
    )

# ── Envío de mensajes ──────────────────────────────────────
def enviar_mensaje(destino, texto):
    try:
        r = requests.post(
            f'https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat',
            data={
                'token': ULTRAMSG_TOKEN,
                'to': destino,
                'body': texto
            },
            timeout=30
        )
        print(f'✅ Mensaje enviado: {r.status_code}')
        return r.status_code in [200, 201]
    except Exception as e:
        print(f'❌ Error enviando mensaje: {e}')
        return False

def enviar_pdf_b64(destino, pdf_b64, placa, autor_numero, desde_cache=False):
    try:
        nombre_autor = MIEMBROS.get(autor_numero, autor_numero)
        ahora = datetime.now().strftime('%d/%m/%Y %I:%M %p')
        cache_tag = '\n⚡ _Resultado en caché_' if desde_cache else ''

        r = requests.post(
            f'https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/document',
            data={
                'token': ULTRAMSG_TOKEN,
                'to': destino,
                'document': f'data:application/pdf;base64,{pdf_b64}',
                'filename': f'Reporte_{placa}.pdf',
                'caption': (
                    f'📄 Reporte vehicular - Placa {placa}\n'
                    f'🙋 Solicitado por: {nombre_autor}\n'
                    f'📅 {ahora}{cache_tag}'
                )
            },
            timeout=120
        )
        print(f'📨 Respuesta UltraMsg: {r.status_code} - {r.text}')
        return r.status_code in [200, 201]
    except Exception as e:
        print(f'❌ ERROR enviando PDF: {e}')
        import traceback
        traceback.print_exc()
        return False

# ── Procesar consulta ──────────────────────────────────────
def procesar_consulta(placa, destino, autor):
    inicio = time.time()

    # Verificar caché primero
    cached = obtener_cache(placa)
    if cached:
        print(f'⚡ Placa {placa} encontrada en caché')
        if enviar_pdf_b64(destino, cached['pdf_b64'], placa, autor, desde_cache=True):
            registrar_log(autor, placa, 'cache_hit', 0)
        else:
            enviar_mensaje(destino, f'❌ Error enviando PDF para *{placa}*')
            registrar_log(autor, placa, 'error_envio_cache', 0)
        return

    try:
        # consulta.py luego manejará sesión persistente / relogin
        pdf_path = ejecutar_consulta_completa(placa, USUARIO_CV, CONTRASENA_CV)
        segundos = int(time.time() - inicio)

        if pdf_path and os.path.exists(pdf_path):
            print(f'✅ PDF generado en: {pdf_path}')
            time.sleep(1.5)

            with open(pdf_path, 'rb') as f:
                pdf_b64 = base64.b64encode(f.read()).decode('utf-8')

            guardar_cache(placa, pdf_b64)

            if enviar_pdf_b64(destino, pdf_b64, placa, autor):
                print('✅ PDF enviado exitosamente')
                registrar_log(autor, placa, 'exitoso', segundos)
            else:
                enviar_mensaje(destino, f'❌ Error enviando PDF para *{placa}*')
                registrar_log(autor, placa, 'error_envio', segundos)

            try:
                os.remove(pdf_path)
            except Exception:
                pass
        else:
            enviar_mensaje(destino, f'⚠️ No se pudo generar reporte para *{placa}*.')
            registrar_log(autor, placa, 'sin_pdf', segundos)

    except Exception as e:
        segundos = int(time.time() - inicio)
        print(f'❌ Error en procesar_consulta: {e}')
        import traceback
        traceback.print_exc()
        enviar_mensaje(destino, f'❌ Error al consultar *{placa}*.')
        registrar_log(autor, placa, 'excepcion', segundos)

# ── Webhook ────────────────────────────────────────────────
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json or {}
        msg_data = data.get('data', {})

        # Solo del grupo autorizado
        if msg_data.get('from') != GRUPO_AUTORIZADO:
            print(f'🚫 Ignorado (no autorizado): {msg_data.get("from")}')
            return jsonify({'status': 'ignorado'}), 200

        # Ignorar mensajes propios
        if msg_data.get('fromMe'):
            return jsonify({'status': 'ignorado'}), 200

        body = (msg_data.get('body') or '').strip()
        body_up = body.upper()
        autor = extraer_numero_autor(msg_data)

        print(f'📩 Mensaje de {autor}: {body_up}')

        if not body_up.startswith('CONSULTA '):
            return jsonify({'status': 'ok'}), 200

        placa = normalizar_placa(body_up.replace('CONSULTA ', '', 1))

        if not placa_valida(placa):
            enviar_mensaje(GRUPO_AUTORIZADO, '⚠️ Formato: *CONSULTA ABC123*')
            return jsonify({'status': 'formato_invalido'}), 200

        # Si ya está en caché, enviar directo sin cola
        cached = obtener_cache(placa)
        if cached:
            print(f'⚡ Caché directo para {placa}')
            ok = enviar_pdf_b64(
                GRUPO_AUTORIZADO,
                cached['pdf_b64'],
                placa,
                autor,
                desde_cache=True
            )
            if ok:
                registrar_log(autor, placa, 'cache_directo', 0)
                return jsonify({'status': 'cache_directo'}), 200
            else:
                enviar_mensaje(GRUPO_AUTORIZADO, f'❌ Error enviando PDF en caché para *{placa}*')
                return jsonify({'status': 'cache_error'}), 200

        # Evitar duplicados de la misma placa
        if placa_esta_activa(placa):
            enviar_mensaje(
                GRUPO_AUTORIZADO,
                f'⏳ La placa *{placa}* ya está en proceso o en cola. Espera un momento.'
            )
            return jsonify({'status': 'duplicada'}), 200

        # Verificar límite diario
        if not verificar_limite(autor):
            nombre = MIEMBROS.get(autor, autor)
            enviar_mensaje(
                GRUPO_AUTORIZADO,
                f'🚫 *{nombre}* alcanzaste el límite de {LIMITE_DIARIO} consultas por hoy.\n'
                f'🔄 Tu contador se resetea a medianoche.'
            )
            return jsonify({'status': 'limite_alcanzado'}), 200

        # Marcar placa activa y encolar
        activar_placa(placa)

        posicion = cola.qsize() + 1
        if posicion > 1:
            enviar_mensaje(
                GRUPO_AUTORIZADO,
                f'📋 Placa *{placa}* añadida a la cola\n'
                f'⏳ Posición #{posicion}'
            )
        else:
            enviar_mensaje(
                GRUPO_AUTORIZADO,
                f'⏳ Consultando *{placa}*...\nEspera unos minutos.'
            )

        cola.put((placa, GRUPO_AUTORIZADO, autor))
        return jsonify({'status': 'ok'}), 200

    except Exception as e:
        print(f'❌ Error en webhook: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error'}), 500

# ── Health check ───────────────────────────────────────────
@app.route('/health', methods=['GET'])
def health():
    with lock_placas:
        placas_actuales = list(placas_activas)

    with lock_cache:
        placas_cache = list(cache_pdfs.keys())

    return jsonify({
        'status': 'ok',
        'grupo': GRUPO_AUTORIZADO,
        'cola_pendientes': cola.qsize(),
        'placas_en_proceso_o_cola': placas_actuales,
        'cache_placas': placas_cache,
        'pausa_min_seg': PAUSA_MIN_SEG,
        'pausa_max_seg': PAUSA_MAX_SEG
    }), 200

# ── Inicio ─────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f'🚀 Servidor iniciando en puerto {port}')
    print(f'📍 Grupo autorizado: {GRUPO_AUTORIZADO}')
    print(f'⏱️ Pausa entre consultas: {PAUSA_MIN_SEG}s a {PAUSA_MAX_SEG}s')
    app.run(host='0.0.0.0', port=port, debug=False)
