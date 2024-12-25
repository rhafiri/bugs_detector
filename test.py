from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

app = Flask(__name__)
CORS(app)  # Autoriser les requêtes depuis d'autres origines
socketio = SocketIO(app, cors_allowed_origins="*")  # Permet d'utiliser les WebSockets

# Initialisation du tableau avec deux objets vides
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

        # Vérifier que la valeur 'x' existe dans les données
        if 'x' in data:
            # Convertir 'x' en entier (au cas où il est reçu en tant que chaîne)
            x = int(data['x'])

            # Déterminer l'index basé sur la valeur de x
            if x == 1:
                index = 0
            elif x == 2:
                index = 1
            else:
                return jsonify({"error": "Valeur de x invalide, elle doit être 1 ou 2"}), 400

            # Mettre à jour les données dans l'index approprié
            detection_data[index]['detection'] = data.get('detection', detection_data[index]['detection'])
            detection_data[index]['x'] = data['x']
            detection_data[index]['y'] = data.get('y', detection_data[index]['y'])

            # Afficher les données mises à jour
            print(f"Index {index} mis à jour : {detection_data[index]}")

            # Émettre les nouvelles données à tous les clients connectés via WebSocket
            socketio.emit('update_detection', detection_data, broadcast=True)  # broadcast=True pour envoyer à tous les clients

            return jsonify({"message": f"Données mises à jour à l'index {index} avec succès"}), 200
        else:
            return jsonify({"error": "La valeur 'x' est requise"}), 400

    except Exception as e:
        print(f"Erreur : {e}")
        return jsonify({"error": "Erreur lors de la réception des données"}), 400

@app.route('/get_detection', methods=['GET'])
def send_detection():
    # Retourne le tableau de données actuel
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
