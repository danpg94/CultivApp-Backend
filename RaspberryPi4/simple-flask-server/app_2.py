#Simple Flask test program
# connect to 

import subprocess
from flask_json_schema import JsonSchema, JsonValidationError
from flask import Flask, request, jsonify
from datetime import datetime
import time

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import ConnectionFailure

app = Flask(__name__)
schema = JsonSchema(app)

# Attempt to connect to local Mongo database
try:
    client = MongoClient("mongodb://dan:test@0.0.0.0:27017", server_api=ServerApi('1'))
    client.admin.command('ping')
except ConnectionFailure as e:
    print(f"Could not connect to mongoDB database {e}")

# Define database or create database if not exists

plant_db = client["plant_data"]
plant_collection = plant_db["plant_1"]


# Get current assigned IP using hostname command on Linux
y = subprocess.run(['/usr/bin/hostname', '-I'], capture_output=True)
ipAddrs = y.stdout.split()
ip = ipAddrs[0].decode("utf-8")

# Schema for ESP8266 sensor data
ESP8266_sensor_data_schema = {
    "required": ["temp", "rel_hum", "lux", "moi_ana", "moi_percent"],
    "properties": {
        "temp": {"type": 'string'},
        "rel_hum" : {"type": 'string'},
        "lux": {"type": 'string'},
        "moi_ana": {"type": 'string'},
        "moi_percent": {"type": 'string'}
    },
    "validationLevel": "strict",
    "validationAction": "error"
}

# Change to the IP of device running this app
# ip = '192.168.0.7' # Home IP 
# ip = '192.168.0.103' # Lab IP

@app.errorhandler(JsonValidationError)
def validation_error(e):
    return jsonify({'error': e.message, 'errors': [validation_error.message for validation_error in e.errors]}),406

@app.route('/')
@app.route('/index')
def index():
    return f"Raspberry Pi4 4G on {ip}\nAdd /hello for a surprise :)", 200

@app.route('/tick')
def hello():
    return f'Hello, the time is: {datetime.now()}', 200


@app.route('/tock', methods=['POST'])
@schema.validate(ESP8266_sensor_data_schema)
def handle_json():
    if request.method == "POST":
        data = request.json
        unix_timestamp = int(time.time())
        print("Timestamp: " + str(unix_timestamp))
        print("Temperature: " + data.get('temp'))
        print("Relative Humidity: " + data.get('rel_hum'))
        print("Lux: " + data.get('lux'))
        print("Moisture Value: " + data.get('moi_ana'))
        print("Moisture Percent: " + data.get('moi_percent'))
        plant_collection.insert_one(
            {
                "timestamp": unix_timestamp,
                "temperature": data.get('temp'),
                "relative_humidity": data.get('rel_hum'),
                "lux": data.get('lux'),
                "moisture_value": data.get('moi_ana'),
                "moisture_percent": data.get('moi_percent')
            }
        )
        return jsonify({ 'success': True, 'message': 'Added to DB' })


if __name__ == '__main__':
    app.run(debug=True, host=ip)