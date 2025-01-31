from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging
from datetime import datetime
 
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")
logging.basicConfig(level=logging.INFO)
 
# Initialisation des données de détection pour deux cartes
num_points = 2
detection_data = [{"detection": 0, "x": None, "y": None} for _ in range(num_points)]
 
def convert_timestamp_to_datetime(timestamp_ms):
    """Convertit un timestamp en date formatée"""
    try:
        dt = datetime.fromtimestamp(timestamp_ms / 1000)
        return dt.strftime('%d/%m/%Y %H:%M:%S')
    except Exception as e:
        logging.error(f"Erreur conversion timestamp: {e}")
        return str(timestamp_ms)
 
@app.route('/send_detection', methods=['POST'])
def receive_detection():
    global detection_data
    try:
        # Récupérer les données envoyées
        data = request.get_json()
        x_val = float(data.get('x', 0))
        timestamp = float(data.get('y', 0))  # Timestamp reçu
        detection = data.get('detection', 0)
        # Convertir le timestamp en format lisible
        formatted_date = convert_timestamp_to_datetime(timestamp)
        # Identifier la carte en fonction de la valeur de x
        if x_val == 1:  # Carte 1
            detection_data[0] = {
                "detection": detection,
                "x": x_val,
                "y": formatted_date  # Stocker la date formatée au lieu du timestamp
            }
            # Set the same y value for detection 2
            detection_data[1]["y"] = formatted_date
        elif x_val == 2:  # Carte 2
            detection_data[1] = {
                "detection": detection,
                "x": x_val,
                "y": formatted_date  # Stocker la date formatée au lieu du timestamp
            }
            # Set the same y value for detection 1
            detection_data[0]["y"] = formatted_date
        else:
            return jsonify({"error": "Invalid card identifier"}), 400
 
        # Logging des données reçues
        logging.info(f"Received data - x: {x_val}, y: {formatted_date}, detection: {detection}")
        logging.info(f"Updated detection data: {detection_data}")
        # Émission de l'événement Socket.IO
        socketio.emit('update_detection', detection_data, broadcast=True)
        return jsonify({
            "message": "Data updated successfully",
            "data": detection_data
        }), 200
    except ValueError as e:
        logging.error(f"ValueError: {e}")
        return jsonify({"error": "Invalid x or y values"}), 400
    except Exception as e:
        logging.error(f"Error: {e}")
        return jsonify({"error": "Error processing data"}), 400
 
@app.route('/get_detection', methods=['GET'])
def send_detection():
    return jsonify(detection_data)
 
@socketio.on('connect')
def handle_connect():
    logging.info("Client connected")
    emit('update_detection', detection_data)
 
@socketio.on('disconnect')
def handle_disconnect():
    logging.info("Client disconnected")
 
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
