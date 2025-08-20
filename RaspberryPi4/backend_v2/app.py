import subprocess
from flask_json_schema import JsonSchema, JsonValidationError
from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
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


load_dotenv(find_dotenv())

MONGO_DB_LOCAL_USER = os.environ.get("MONGO_DB_LOCAL_USER")
MONGO_DB_LOCAL_PWD = os.environ.get("MONGO_DB_LOCAL_PWD")
MONGO_DB_LOCAL_IP = os.environ.get("MONGO_DB_LOCAL_IP")
MONGO_DB_LOCAL_PORT = os.environ.get("MONGO_DB_LOCAL_PORT")

# URI for the cluster. Remember to have an .env file with user, password and DB name for the local Mongo DB instance
uri = f"mongodb://{MONGO_DB_LOCAL_USER}:{MONGO_DB_LOCAL_PWD}@{MONGO_DB_LOCAL_IP}:{MONGO_DB_LOCAL_PORT}"

scheduler = BackgroundScheduler()

app = Flask(__name__)
schema = JsonSchema(app)

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
plant_collection = plant_db["esp8266_sensor_data"]
device_collection = plant_db["devices"]

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
            job_id = scheduler.add_job(func=curl_post_device, args=[device['latest_ip'], sensor_num], trigger="interval", seconds=10)
            print(f'[LOG] Ping successful, adding to scheduler: {job_id}')
        else:
            print(f'[WARING] Ping unsuccessful, ignoring')

def start_scheduler():
    scheduler.start()
    print("\n[LOG] Attempting to look for devices in DB ...\n")
    devices_entry = list(device_collection.find())
    if len(devices_entry) != 0:
        print(f'[LOG] Found {len(devices_entry)} devices!')
        load_request_jobs(devices_entry)
    else:
        print("[LOG] There are no device entries en the database")

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
                device_collection.update_one({"name": data["dev_mac_addr"]}, {"$set": {"name": data["dev_type"], "mac": data["dev_mac_addr"], "latest_ip": data["session_ip"] , "sensor_list": data["sensors_detected"]}})
            
        return 'Connection OK!', 200


@app.route('/sensor_data', methods=['POST', 'GET', 'DELETE'])
@schema.validate(ESP8266_sensor_data_schema)
def handle_json():
    pass


if __name__ == '__main__':
    start_scheduler()
    app.run(debug=False, host=ip, port=2000, use_reloader=False)