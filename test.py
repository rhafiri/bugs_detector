from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialisation des données
detection_data = [
    {"detection": 0, "x": None, "y": None},  # Index 0
    {"detection": 0, "x": None, "y": None}   # Index 1
]

@app.route('/send_detection', methods=['POST'])
def receive_detection():
    global detection_data
    try:
        # Récupérer les données envoyées par le client
        data = request.get_json()

        # Vérifier que les champs 'x' et 'y' existent
        x = int(data.get('x', -1))
        y = int(data.get('y', -1))

        if x not in [1, 2]:
            return jsonify({"error": "La valeur de 'x' doit être 1 ou 2."}), 400

        # Déterminer l'index dans le tableau
        index = x - 1

        # Mettre à jour uniquement la dernière valeur reçue
        detection_data[index] = {
            "detection": data.get('detection', 0),
            "x": x,
            "y": y
        }

        # Afficher les données mises à jour
        logging.info(f"Index {index} mis à jour : {detection_data[index]}")

        # Émettre les nouvelles données à tous les clients connectés via WebSocket
        socketio.emit('update_detection', detection_data, broadcast=True)

        return jsonify({"message": f"Données mises à jour à l'index {index} avec succès"}), 200
    except ValueError:
        return jsonify({"error": "Valeurs 'x' ou 'y' invalides"}), 400
    except Exception as e:
        logging.error(f"Erreur : {e}")
        return jsonify({"error": "Une erreur est survenue lors du traitement des données"}), 400

@app.route('/get_detection', methods=['GET'])
def send_detection():
    # Retourne le tableau contenant uniquement les dernières données reçues
    return jsonify(detection_data)

@socketio.on('connect')
def handle_connect():
    logging.info("Un client s'est connecté")
    emit('update_detection', detection_data)

@socketio.on('disconnect')
def handle_disconnect():
    logging.info("Un client s'est déconnecté")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
