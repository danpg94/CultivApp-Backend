#Simple Flask test program
# connect to 

import subprocess
from flask_json_schema import JsonSchema, JsonValidationError
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import time

import pycurl
from io import BytesIO
import json

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import ConnectionFailure

scheduler = BackgroundScheduler()

app = Flask(__name__)
schema = JsonSchema(app)

# # Attempt to connect to local Mongo database
try:
    client = MongoClient("mongodb://dan:test@0.0.0.0:27017", server_api=ServerApi('1'))
    client.admin.command('ping')
except ConnectionFailure as e:
    print(f"Could not connect to mongoDB database {e}")

# Define database or create database if not exists

plant_db = client["ver_2bd"]

plant_collection = plant_db["esp8266_sensor_data"]
device_collection = plant_db["device_lists"]

# Get current assigned IP using hostname command on Linux
y = subprocess.run(['/usr/bin/hostname', '-I'], capture_output=True)
ipAddrs = y.stdout.split()
ip = ipAddrs[0].decode("utf-8")

# Schema for ESP8266 sensor data
ESP8266_sensor_data_schema = {
    "required": ["temp", "rel_hum", "lux", "moi_ana"],
    "properties": {
        "sensor_num": {"type": 'string'},
        "temp": {"type": 'string'},
        "rel_hum" : {"type": 'string'},
        "lux": {"type": 'string'},
        "moi_ana": {"type": 'string'},
    },
    "validationLevel": "strict",
    "validationAction": "error"
}

def request_job_curl(device_ip, sensor_num):
    try:
        buffer = BytesIO()
        c = pycurl.Curl()
        url = f'http://{device_ip}/data/'
        data = {"sensor_num": sensor_num}
        json_data = json.dumps(data)

        c.setopt(c.URL, url)
        c.setopt(pycurl.HTTPHEADER, ['Content-Type: application/json']) # Set content type for JSON
        c.setopt(c.POSTFIELDS, json_data)
        c.setopt(c.WRITEFUNCTION, buffer.write)

        c.perform()

        response_body = buffer.getvalue().decode('utf-8')
        print(response_body)
        c.close()
    except pycurl.error as e:
        print(f'[ERROR] Could not connect to device pycurl: {e}')
        c.close()


def load_request_jobs():
    device_ip = '192.168.0.12'
    sensor_num = '0'
    job_id = scheduler.add_job(func=request_job_curl, args=[device_ip, sensor_num], trigger="interval", seconds=30)
    print(job_id)

def start_scheduler():
    print("\nLoading existing jobs...\n")
    load_request_jobs()
    scheduler.start()

@app.teardown_appcontext
def stop_scheduler(exception=None):
    scheduler.shutdown()

@app.errorhandler(JsonValidationError)
def validation_error(e):
    return jsonify({'error': e.message, 'errors': [validation_error.message for validation_error in e.errors]}),406

@app.route('/')
@app.route('/index')
def index():
    return f"Raspberry Pi4 4G on {ip}\nAdd /hello for a surprise :)", 200

@app.route('/device', methods=['POST'])
def recieve_device_info():
    if request.method == "POST":
        data = request.json
        print(f'Device {data["dev_name"]} connected via {data["session_ip"]} at: {datetime.now()}')
        # TODO: Add an entry to device detected db
        
        device_entry = device_collection.find_one({"name": data["dev_name"]})
        print(f'Device entry: {device_entry}')
        if device_entry == None:
            print(f'[NEW DEVICE] New Device detected for: {data["dev_name"]} ')
            device_collection.insert_one({"name": data["dev_name"], "latest_ip": data["session_ip"]})
        else:
            print(f'[UPDATE] New ip detected for: {data["dev_name"]} ')
            device_collection.update_one({"name": data["dev_name"]}, {"$set": {"name": data["dev_name"], "latest_ip": data["session_ip"]}})
            
        return 'Connection OK!', 200


@app.route('/sensor_data', methods=['POST', 'GET', 'DELETE'])
@schema.validate(ESP8266_sensor_data_schema)
def handle_json():
    pass


if __name__ == '__main__':
    start_scheduler()
    app.run(debug=True, host=ip, port=2000)