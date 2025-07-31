from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging
import sqlite3
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*")
logging.basicConfig(level=logging.INFO)

# Database configuration - Use full path to ensure consistency
import os
DB_NAME = os.path.abspath('detections.db')
print(f"Database will be created at: {DB_NAME}")

# Initialisation des données de détection pour deux cartes
num_points = 2
detection_data = [{"detection": 0, "x": None, "y": None} for _ in range(num_points)]

def init_database():
    """Initialize the SQLite database with detections table"""
    try:
        logging.info(f"Database path: {DB_NAME}")
        logging.info(f"Database exists before init: {os.path.exists(DB_NAME)}")
        
        # Check if we can write to the directory
        db_dir = os.path.dirname(DB_NAME)
        if not db_dir:  # If DB_NAME is just a filename, use current directory
            db_dir = os.getcwd()
        logging.info(f"Database directory: {db_dir}")
        logging.info(f"Directory writable: {os.access(db_dir, os.W_OK)}")
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Create table with IF NOT EXISTS
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                detection INTEGER NOT NULL,
                timestamp_ms INTEGER NOT NULL,
                datetime_formatted TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        
        # Verify table was created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='detections'")
        table_exists = cursor.fetchone()
        logging.info(f"Table 'detections' exists after creation: {table_exists is not None}")
        
        # Check if data exists after creation
        cursor.execute("SELECT COUNT(*) FROM detections")
        count = cursor.fetchone()[0]
        logging.info(f"Records in database after init: {count}")
        
        # Show file size to verify it's actually being written
        if os.path.exists(DB_NAME):
            file_size = os.path.getsize(DB_NAME)
            logging.info(f"Database file size: {file_size} bytes")
        
        conn.close()
        return True
        
    except Exception as e:
        logging.error(f"Database initialization error: {e}")
        return False

def save_detection_to_db(card_id, detection, timestamp_ms, formatted_date):
    """Save detection data to SQLite database"""
    try:
        # Debug: Log current working directory and database path
        current_dir = os.getcwd()
        logging.info(f"Current working directory: {current_dir}")
        logging.info(f"Attempting to write to database: {DB_NAME}")
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO detections (card_id, detection, timestamp_ms, datetime_formatted)
            VALUES (?, ?, ?, ?)
        ''', (card_id, detection, timestamp_ms, formatted_date))
        
        conn.commit()
        conn.close()
        
        # IMMEDIATE verification after insert
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM detections")
        count_after_insert = cursor.fetchone()[0]
        cursor.execute("SELECT * FROM detections WHERE card_id = ? ORDER BY created_at DESC LIMIT 1", (card_id,))
        last_inserted = cursor.fetchone()
        conn.close()
        
        logging.info(f"Saved to DB - Card: {card_id}, Detection: {detection}, Time: {formatted_date}")
        logging.info(f"Total records after insert: {count_after_insert}")
        logging.info(f"Last inserted record: {last_inserted}")
        
        # Check file metadata
        if os.path.exists(DB_NAME):
            file_size = os.path.getsize(DB_NAME)
            mod_time = os.path.getmtime(DB_NAME)
            logging.info(f"Database file size after insert: {file_size} bytes, modified: {mod_time}")
        
        return True
    except Exception as e:
        logging.error(f"Database error: {e}")
        logging.error(f"Failed to save - Card: {card_id}, Detection: {detection}")
        return False

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
            # Save to database
            save_detection_to_db(1, detection, timestamp, formatted_date)
            
        elif x_val == 2:  # Carte 2
            detection_data[1] = {
                "detection": detection,
                "x": x_val,
                "y": formatted_date  # Stocker la date formatée au lieu du timestamp
            }
            # Set the same y value for detection 1
            detection_data[0]["y"] = formatted_date
            # Save to database
            save_detection_to_db(2, detection, timestamp, formatted_date)
            
        else:
            return jsonify({"error": "Invalid card identifier"}), 400

        # Logging des données reçues
        logging.info(f"Received data - x: {x_val}, y: {formatted_date}, detection: {detection}")
        logging.info(f"Updated detection data: {detection_data}")
        
        # Émission de l'événement Socket.IO (without broadcast parameter)
        socketio.emit('update_detection', detection_data)
        
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
    """Get the most recent detection data from database in the required format"""
    try:
        # Ensure database exists before querying
        init_database()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Get the most recent detection for each card (latest timestamp)
        cursor.execute('''
            SELECT 
                card_id, 
                detection, 
                datetime_formatted,
                timestamp_ms
            FROM detections d1
            WHERE timestamp_ms = (
                SELECT MAX(timestamp_ms) 
                FROM detections d2 
                WHERE d2.card_id = d1.card_id
            )
            ORDER BY card_id
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        logging.info(f"Latest detection data from DB: {results}")
        
        # Create the response format
        formatted_data = []
        
        # Initialize with default values for both cards
        card_data = {
            1: {"detection": "0", "x": 1.0, "y": "01/01/1970 00:00:00"}, 
            2: {"detection": "0", "x": 2.0, "y": "01/01/1970 00:00:00"}
        }
        
        # Update with actual data from database
        for row in results:
            card_id = row[0]
            detection = str(row[1])  # Convert to string as required
            datetime_formatted = row[2]
            
            card_data[card_id] = {
                "detection": detection,
                "x": float(card_id),
                "y": datetime_formatted
            }
        
        # Convert to list format (card 1 first, then card 2)
        formatted_data = [
            card_data[1],
            card_data[2]
        ]
        
        logging.info(f"Formatted response: {formatted_data}")
        return jsonify(formatted_data)
        
    except Exception as e:
        logging.error(f"Error getting detection data from DB: {e}")
        # Return default structure if database error
        return jsonify([
            {"detection": "0", "x": 1.0, "y": "01/01/1970 00:00:00"},
            {"detection": "0", "x": 2.0, "y": "01/01/1970 00:00:00"}
        ])

@app.route('/detections_per_day', methods=['GET'])
def get_detections_per_day():
    """Get detection count grouped by day"""
    try:
        # Ensure database exists before querying
        init_database()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Get optional date filter from query parameters
        start_date = request.args.get('start_date')  # Format: YYYY-MM-DD
        end_date = request.args.get('end_date')      # Format: YYYY-MM-DD
        card_id = request.args.get('card_id')        # Optional card filter
        
        query = '''
            SELECT 
                DATE(datetime(timestamp_ms/1000, 'unixepoch')) as date,
                card_id,
                COUNT(CASE WHEN detection = 1 THEN 1 END) as detections_count,
                COUNT(*) as total_records
            FROM detections
            WHERE 1=1
        '''
        params = []
        
        if start_date:
            query += " AND DATE(datetime(timestamp_ms/1000, 'unixepoch')) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(datetime(timestamp_ms/1000, 'unixepoch')) <= ?"
            params.append(end_date)
            
        if card_id:
            query += " AND card_id = ?"
            params.append(int(card_id))
        
        query += " GROUP BY DATE(datetime(timestamp_ms/1000, 'unixepoch')), card_id ORDER BY date DESC"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Format results
        daily_data = []
        for row in results:
            daily_data.append({
                "date": row[0],
                "card_id": row[1],
                "detections_count": row[2],
                "total_records": row[3]
            })
        
        conn.close()
        
        return jsonify({
            "daily_detections": daily_data,
            "total_days": len(set([item["date"] for item in daily_data]))
        }), 200
        
    except Exception as e:
        logging.error(f"Error getting daily detections: {e}")
        return jsonify({"error": "Error retrieving daily data"}), 500

@app.route('/detections_per_hour', methods=['GET'])
def get_detections_per_hour():
    """Get detection count grouped by hour of the day (incremental differences)"""
    try:
        # Ensure database exists before querying
        init_database()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Get optional date filter from query parameters
        date = request.args.get('date')  # Format: YYYY-MM-DD
        logging.info(f"Date filter requested: {date}")
        
        # Get DISTINCT detections ordered by timestamp to avoid duplicates
        query = '''
            SELECT 
                card_id,
                detection,
                timestamp_ms,
                strftime('%H', datetime(timestamp_ms/1000, 'unixepoch')) as hour,
                DATE(datetime(timestamp_ms/1000, 'unixepoch')) as date
            FROM detections
            WHERE 1=1
        '''
        params = []
        
        if date:
            query += " AND DATE(datetime(timestamp_ms/1000, 'unixepoch')) = ?"
            params.append(date)
        
        # Group by card_id, timestamp_ms to get unique readings per timestamp
        query += " GROUP BY card_id, timestamp_ms ORDER BY card_id, timestamp_ms"
        
        logging.info(f"Executing query: {query} with params: {params}")
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        logging.info(f"Deduplicated data from database: {results}")
        
        # Calculate incremental differences for each card
        hourly_data = {}
        for hour in range(24):
            hourly_data[hour] = {"Trap 1": 0, "Trap 2": 0}
        
        # Process data for each card separately
        card_data = {1: [], 2: []}
        for row in results:
            card_id = row[0]
            detection = row[1]
            timestamp_ms = row[2]
            hour = int(row[3])
            card_data[card_id].append((detection, timestamp_ms, hour))
        
        # Calculate incremental differences for each card
        for card_id in [1, 2]:
            trap_name = f"Trap {card_id}"
            data_points = card_data[card_id]
            
            logging.info(f"Processing {trap_name} with {len(data_points)} unique data points: {data_points}")
            
            for i in range(len(data_points)):
                current_detection = data_points[i][0]
                current_hour = data_points[i][2]
                
                if i == 0:
                    # First reading: use the detection value as-is
                    increment = current_detection
                    logging.info(f"{trap_name} - First reading at hour {current_hour}: {current_detection} (using as increment: {increment})")
                else:
                    # Calculate difference from previous reading
                    previous_detection = data_points[i-1][0]
                    increment = current_detection - previous_detection
                    logging.info(f"{trap_name} - Hour {current_hour}: current={current_detection}, previous={previous_detection}, increment={increment}")
                
                # Handle negative increments (sensor reset or error)
                if increment < 0:
                    logging.warning(f"{trap_name} - Negative increment detected: {increment}. Using current value instead.")
                    increment = current_detection  # Use current value when sensor resets
                
                # Add increment to the hour
                if card_id == 1:
                    hourly_data[current_hour]["Trap 1"] += increment
                elif card_id == 2:
                    hourly_data[current_hour]["Trap 2"] += increment
        
        logging.info(f"Final hourly data: {hourly_data}")
        
        # Format the response as requested
        result = []
        for hour in range(24):
            hour_str = f"{hour:02d}:00"
            result.append({
                "name": hour_str,
                "Trap 1": hourly_data[hour]["Trap 1"],
                "Trap 2": hourly_data[hour]["Trap 2"]
            })
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error getting hourly detections: {e}")
        # Return default structure with all zeros if error
        result = []
        for hour in range(24):
            hour_str = f"{hour:02d}:00"
            result.append({
                "name": hour_str,
                "Trap 1": 0,
                "Trap 2": 0
            })
        return jsonify(result)

@socketio.on('connect')
def handle_connect():
    logging.info("Client connected")
    emit('update_detection', detection_data)

@socketio.on('disconnect')
def handle_disconnect():
    logging.info("Client disconnected")

if __name__ == '__main__':
    # Initialize database on startup
    print("=" * 50)
    print("STARTING APPLICATION")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python executable: {os.sys.executable}")
    print(f"Database path: {DB_NAME}")
    print("=" * 50)
    
    # Check if database exists BEFORE init
    if os.path.exists(DB_NAME):
        file_size = os.path.getsize(DB_NAME)
        mod_time = os.path.getmtime(DB_NAME)
        print(f"Existing database found - Size: {file_size} bytes, Modified: {mod_time}")
    else:
        print("No existing database found")
    
    init_database()
    logging.info("Database initialized")
    
    # Double-check database has data if any
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM detections")
        startup_count = cursor.fetchone()[0]
        logging.info(f"Application startup - Total records: {startup_count}")
        
        if startup_count > 0:
            cursor.execute("SELECT * FROM detections ORDER BY created_at DESC LIMIT 3")
            recent_data = cursor.fetchall()
            logging.info(f"Most recent records: {recent_data}")
        
        conn.close()
    except Exception as e:
        logging.error(f"Startup database check error: {e}")
    
    print("Starting Flask server...")
    # DISABLE auto-reloader to prevent multiple process issues
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)