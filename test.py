from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

app = Flask(__name__)
CORS(app)  # Autoriser les requêtes depuis d'autres origines
socketio = SocketIO(app, cors_allowed_origins="*")  # Permet d'utiliser les WebSockets

# Stockage des données de détection avec x et y
detection_data = {"detection": 0, "x": None, "y": None}

@app.route('/send_detection', methods=['POST'])
def receive_detection():
    global detection_data
    try:
        # Récupérer les données envoyées par le client
        data = request.get_json()

        # Mettre à jour la valeur 'detection' (toujours mise à jour)
        if 'detection' in data:
            detection_data['detection'] = data['detection']

        # Mettre à jour x et y uniquement si elles ne sont pas encore définies
        if detection_data['x'] is None and 'x' in data:
            detection_data['x'] = data['x']
        if detection_data['y'] is None and 'y' in data:
            detection_data['y'] = data['y']

        # Afficher les données reçues
        print(f"Détection : {detection_data['detection']}, x: {detection_data['x']}, y: {detection_data['y']}")

        # Émettre les nouvelles données à tous les clients connectés via WebSocket
        socketio.emit('update_detection', detection_data, broadcast=True)  # broadcast=True pour envoyer à tous les clients

        return jsonify({"message": "Données reçues avec succès"}), 200

    except Exception as e:
        print(f"Erreur : {e}")
        return jsonify({"error": "Erreur lors de la réception des données"}), 400

@app.route('/get_detection', methods=['GET'])
def send_detection():
    # Retourne les données actuelles de détection
    return jsonify(detection_data)

@socketio.on('connect')
def handle_connect():
    print("Un client s'est connecté")
    emit('update_detection', detection_data)  # Envoyer les données actuelles lors de la connexion

@socketio.on('disconnect')
def handle_disconnect():
    print("Un client s'est déconnecté")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
