import subprocess
from flask_json_schema import JsonSchema, JsonValidationError
from flask import Flask, request, jsonify
from flask_apscheduler import APScheduler
from datetime import datetime

import time
import os
from dotenv import load_dotenv, find_dotenv

import pycurl
from io import BytesIO
import json

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import ConnectionFailure

class APScheduler_Config:
    SCHEDULER_API_ENABLED = True


load_dotenv(find_dotenv())

MONGO_DB_LOCAL_USER = os.environ.get("MONGO_DB_LOCAL_USER")
MONGO_DB_LOCAL_PWD = os.environ.get("MONGO_DB_LOCAL_PWD")
MONGO_DB_LOCAL_IP = os.environ.get("MONGO_DB_LOCAL_IP")
MONGO_DB_LOCAL_PORT = os.environ.get("MONGO_DB_LOCAL_PORT")

# URI for the cluster. Remember to have an .env file with user, password and DB name for the local Mongo DB instance
uri = f"mongodb://{MONGO_DB_LOCAL_USER}:{MONGO_DB_LOCAL_PWD}@{MONGO_DB_LOCAL_IP}:{MONGO_DB_LOCAL_PORT}"

app = Flask(__name__)
schema = JsonSchema(app)

scheduler = APScheduler()


# # Attempt to connect to local Mongo database
print(f'[LOG] Attempting to connect to MongoDB on {uri}')
try:
    client = MongoClient(uri,
                         server_api=ServerApi('1'),
                         serverSelectionTimeoutMS=5000,
                         connectTimeoutMS=5000,
                         socketTimeoutMS=5000)
    client.admin.command('ping')
except ConnectionFailure as e:
    print(f"[ERROR] Could not connect to mongoDB database {e}")

# Define database or create database if not exists

plant_db = client["ver_2bd"]

# Define collection or create collection if not exists
plant_collection = plant_db["plants"]
device_collection = plant_db["devices"]
garden_collection = plant_db["gardens"]
plant_data_collection = plant_db["plant_data"]


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

def curl_post_device(device_ip, sensor_num):
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
        print(f'[ OK ] Recieved response from {device_ip}: {response_body}')
        c.close()
    except pycurl.error as e:
        print(f'[ERROR] Could not connect to device pycurl: {e}')
        c.close()

def curl_ping_device(device_ip):
    try:
        buffer = BytesIO()
        c = pycurl.Curl()
        url = f'http://{device_ip}/ping/'

        c.setopt(c.URL, url)
        c.setopt(c.WRITEDATA, buffer)
        c.perform()

        response_body = buffer.getvalue().decode('utf-8')
        # print(response_body)

        c.close()
        return True
    except pycurl.error as e:
        print(f'[ERROR] Could not connect to device pycurl: {e}')
        c.close()
        return False

def load_request_jobs(devices_entry):
    sensor_num = '0'
    for device in devices_entry:
        print(f'[LOG] Pinging {device["name"]} on {device["latest_ip"]}')
        if curl_ping_device(device['latest_ip']):
            job_id = scheduler.add_job(id='sensor_ping_test_1' ,func=curl_post_device, args=[device['latest_ip'], sensor_num], trigger="interval", seconds=10)
            print(f'[LOG] Ping successful, adding to scheduler: {job_id}')
        else:
            print(f'[WARING] Ping unsuccessful, ignoring')

def load_scheduler_jobs_at_startup():
    print("\n[LOG] Attempting to look for devices in DB ...\n")
    devices_entry = list(device_collection.find())
    if len(devices_entry) != 0:
        print(f'[LOG] Found {len(devices_entry)} devices!')
        load_request_jobs(devices_entry)
    else:
        print("[LOG] There are no device entries en the database")

# This causes scheduler shutdown when there is any other call to the app, ex. /scheduler
# @app.teardown_appcontext
# def stop_scheduler(exception=None):
#     scheduler.shutdown()

@app.errorhandler(JsonValidationError)
def validation_error(e):
    return jsonify({'error': e.message, 'errors': [validation_error.message for validation_error in e.errors]}),406

@app.route('/')
@app.route('/index')
def index():
    return f"Raspberry Pi4 4G on {ip}\nAdd /hello for a surprise :)", 200

# [TODO] Change this to a better health_check instead of a device handler
@app.route('/health_check', methods=['POST'])
def recieve_device_info():
    if request.method == "POST":
        data = request.json
        print(f'[LOG] Device {data["dev_type"]} with MAC {data["dev_mac_addr"]} connected via {data["session_ip"]} at: {datetime.now()}')
        device_entry = device_collection.find_one({"mac": data["dev_mac_addr"]})
        print(f'[DEBUG] [LOG] Device entry: {device_entry}')
        if device_entry == None:
            print(f'[NEW DEVICE] New {data["dev_type"]} Device detected with MAC: {data["dev_mac_addr"]} on {data["session_ip"]}')
            device_collection.insert_one({"name": data["dev_type"], "mac": data["dev_mac_addr"], "latest_ip": data["session_ip"], "sensor_list": data["sensors_detected"]})
        else:
            if data['session_ip'] == device_entry['latest_ip']:
                print(f'[ OK ] Connecting {data["dev_type"]} device to {data["dev_mac_addr"]} on {data["session_ip"]}')
            else:
                print(f'[UPDATE] New ip detected for {data["dev_type"]} with MAC: {data["dev_mac_addr"]} on  {data["session_ip"]}. Previous was {device_entry["latest_ip"]}')
                device_collection.update_one({"mac": data["dev_mac_addr"]}, {"$set": {"name": data["dev_type"], "mac": data["dev_mac_addr"], "latest_ip": data["session_ip"] , "sensor_list": data["sensors_detected"]}})
            
        return 'Connection OK!', 200

@app.route('/device', methods=['POST', 'UPDATE', 'DELETE', 'GET'])
def device_handler():
    if request.method == 'POST':
        print(f'[DEVICE][POST] Device Entry detected')
        # [TODO]
        return 'Not implemented yet\n', 501
    elif request.method == 'GET':
        print(f'[DEVICE][GET] Device list request')
        devices = list(device_collection.find({}, {'_id': 0}))
        print(f'[DEVICE][GET] {devices}\n')
        return jsonify(devices), 200
    elif request.method == 'DELETE':
        # [TODO]
        return 'Not implemented yet\n', 501
    elif request.method == 'UPDATE':
        # [TODO]
        return 'Not implemented yet\n', 501
    else:
        return 'Not Found\n', 404


@app.route('/garden', methods=['POST', 'UPDATE', 'DELETE', 'GET'])
def garden_handler():
    if request.method == 'POST':
        # [TODO]
        return 'Not implemented yet\n', 501
    elif request.method == 'GET':
        print(f'[GARDEN][GET] Garden list request')
        devices = list(garden_collection.find({}, {'_id': 0}))
        print(f'[GARDEN][GET] {devices}\n')
        return jsonify(devices), 200
    elif request.method == 'DELETE':
        # [TODO]
        return 'Not implemented yet\n', 501
    elif request.method == 'UPDATE':
        # [TODO]
        return 'Not implemented yet\n', 501
    else:
        return 'Not Found\n', 404

@app.route('/plant', methods=['POST', 'UPDATE', 'DELETE', 'GET'])
def plant_handler():
    if request.method == 'POST':
        # [TODO]
        return 'Not implemented yet\n', 501
    elif request.method == 'GET':
        print(f'[PLANT][GET] Plant list request')
        devices = list(plant_collection.find({}, {'_id': 0}))
        print(f'[PLANT][GET] {devices}\n')
        return jsonify(devices), 200
    elif request.method == 'DELETE':
        # [TODO]
        return 'Not implemented yet\n', 501
    elif request.method == 'UPDATE':
        # [TODO]
        return 'Not implemented yet\n', 501
    else:
        return 'Not Found\n', 404

@app.route('/plant_data', methods=['POST', 'GET', 'DELETE'])
@schema.validate(ESP8266_sensor_data_schema)
def plant_data_handler():
    if request.method == 'POST':
        data = request.json
        unix_timestamp = int(time.time())
        print("Sensor Number: " + data.get('sensor_num'))
        print("Timestamp: " + str(unix_timestamp))
        print("Temperature: " + data.get('temp'))
        print("Relative Humidity: " + data.get('rel_hum'))
        print("Lux: " + data.get('lux'))
        print("Moisture Value: " + data.get('moi_ana'))
        plant_data_collection.insert_one(
            {
                "timestamp": unix_timestamp,
                "temperature": data.get('temp'),
                "relative_humidity": data.get('rel_hum'),
                "lux": data.get('lux'),
                "moisture_value": data.get('moi_ana'),
                "sensor_num": data.get('sensor_num')
            }
        )

        return jsonify({ 'success': True, 'message': 'Added to DB' }), 200
    elif request.method == 'GET':
        print(f'[PLANT_DATA][GET] Plant list request')
        devices = list(plant_data_collection.find({}, {'_id': 0}))
        print(f'[PLANT_DATA][GET] {devices}\n')
        return jsonify(devices), 200
    elif request.method == 'DELETE':
        # [TODO]
        return 'Not implemented yet\n', 501
    else:
        return 'Not Found\n', 404


@scheduler.task("interval", id="do_job_1", minutes=24, misfire_grace_time=900)
def job1():
    """Sample job 1."""
    print("Job 1 executed")

if __name__ == '__main__':
    scheduler.api_enabled = True
    scheduler.init_app(app)
    load_scheduler_jobs_at_startup()
    scheduler.start()
    app.run(debug=False, host=ip, port=2000, use_reloader=False)