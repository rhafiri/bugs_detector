from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")

logging.basicConfig(level=logging.INFO)

# Initialisation des données de détection pour deux cartes
num_points = 2
detection_data = [{"detection": 0, "x": None, "y": None} for _ in range(num_points)]

@app.route('/send_detection', methods=['POST'])
def receive_detection():
    global detection_data
    try:
        # Récupérer les données envoyées par la carte
        data = request.get_json()
        x_val = float(data.get('x', 0))
        y_val = float(data.get('y', 0))
        detection = data.get('detection', 0)

        # Identifier la carte en fonction de la valeur de x
        if x_val == 1:  # Carte 1
            detection_data[0] = {
                "detection": detection,
                "x": x_val,
                "y": y_val
            }
        elif x_val == 2:  # Carte 2
            detection_data[1] = {
                "detection": detection,
                "x": x_val,
                "y": y_val
            }
        else:
            return jsonify({"error": "Invalid card identifier"}), 400

        # Logging et émission de l'événement Socket.IO
        logging.info(f"Updated detection data: {detection_data}")
        socketio.emit('update_detection', detection_data, broadcast=True)

        return jsonify({"message": "Data updated successfully", "data": detection_data}), 200

    except ValueError:
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
