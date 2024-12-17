from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Autoriser les requêtes depuis d'autres origines (pour le designer)

# Stockage des données de détection avec x et y
detection_data = {"detection": 0, "x": 0.0, "y": 0.0}  

@app.route('/send_detection', methods=['POST'])
def receive_detection():
    global detection_data
    try:
        # Récupérer les données envoyées par le client
        data = request.get_json()
        
        # Mettre à jour les données de détection
        detection_data['detection'] = data['detection']
        detection_data['x'] = data['x']
        detection_data['y'] = data['y']

        # Afficher les nouvelles données de détection
        print(f"Nouvelle détection reçue : {detection_data['detection']}, x: {detection_data['x']}, y: {detection_data['y']}")
        
        return jsonify({"message": "Données reçues avec succès"}), 200
    except Exception as e:
        print(f"Erreur : {e}")
        return jsonify({"error": "Erreur lors de la réception des données"}), 400

@app.route('/get_detection', methods=['GET'])
def send_detection():
    # Retourne les données actuelles de détection, y compris x et y
    return jsonify(detection_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
