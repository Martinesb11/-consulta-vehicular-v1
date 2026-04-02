from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    print("🔥 WEBHOOK ENTRÓ", flush=True)
    print("RAW:", request.get_data(as_text=True), flush=True)
    print("JSON:", request.get_json(silent=True), flush=True)
    return jsonify({'status': 'ok'}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    print("🔥 APP DEBUG REALMENTE INICIADA", flush=True)
    app.run(host='0.0.0.0', port=8080, debug=False)
