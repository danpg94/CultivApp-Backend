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
import uuid

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
                         socketTimeoutMS=5000, 
                         uuidRepresentation='standard'
                         )
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

# Shema for plant registration data
plant_registration_shcema = {
    "required": ["plant_name", "plant_type", "date_planted", "plant_update_poll", "device_mac", "soil_sens_num"],
    "properties": {
        "plant_name": {"type": 'string'},
        "plant_type": {"type": 'string'},
        "date_planed": {"type": 'string'},
        "plant_update_poll": {"type": 'string'},
        "device_mac": {"type": 'string'},
        "soil_sens_num": {"type": 'string'}
    },
    "validationLevel": "strict",
    "validationAction": "error" 
}

def curl_post_device(plant_id, device_ip, sensor_num):
    try:
        buffer = BytesIO()
        c = pycurl.Curl()
        url = f'http://{device_ip}/data/'
        data = {"sensor_num": sensor_num, "plant_id": plant_id}
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

def load_request_jobs(plants_entry):
    for plant in plants_entry:
        device = device_collection.find_one({'mac': plant['device_mac']})
        if device is not None:
            if curl_ping_device(device['latest_ip']):
                print(f'[LOG] Pinging {plant["plant_name"]} on {device["latest_ip"]}')
                job_id = scheduler.add_job(id=f'{plant["plant_name"]}' ,func=curl_post_device, args=[plant['plant_id'],device['latest_ip'], plant['soil_sens_num']], trigger="interval", seconds=plant['plant_update_poll'])
                print(f'[LOG] Ping successful, adding to scheduler: {job_id}')
            else:
                print(f'[WARING] Ping unsuccessful, ignoring')
        else:
            print('[WARN] Could not find device assigned to plant! Skipping scheduling job')

def load_scheduler_jobs_at_startup():
    print("\n[LOG] Attempting to look for plant entries in DB ...\n")
    plants_entry = list(plant_collection.find())
    if len(plants_entry) != 0:
        print(f'[LOG] Found {len(plants_entry)} plants!')
        load_request_jobs(plants_entry)
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
        gardens = list(garden_collection.find({}, {'_id': 0}))
        print(f'[GARDEN][GET] {gardens}\n')
        return jsonify(gardens), 200
    elif request.method == 'DELETE':
        # [TODO]
        return 'Not implemented yet\n', 501
    elif request.method == 'UPDATE':
        # [TODO]
        return 'Not implemented yet\n', 501
    else:
        return 'Not Found\n', 404

@app.route('/plant', methods=['POST', 'UPDATE', 'DELETE', 'GET'])
@schema.validate(plant_registration_shcema)
def plant_handler():
    if request.method == 'POST':
        # [TODO]
        data = request.json
        assigned_uuid = str(uuid.uuid4()).split('-')[0]
        print(f'[PLANT][POST] Recieved new Plant')
        print(f"\tUUID: {assigned_uuid}")
        print(f"\tPlant Name: {data.get('plant_name')}")
        print(f"\tPlant Type: {data.get('plant_type')}")
        print(f"\tDate Planted: {data.get('plant_date')}")
        print(f"\tDate Registered: {data.get('plant_registered')}")
        print(f"\tData Update: {data.get('plant_update_poll')}")
        print(f"\tData Polling activated: {data.get('update_poll_activated')}")
        print(f"\tDevice Id (MAC): {data.get('device_mac')}")
        print(f"\tSensor number: {data.get('soil_sens_num')}")
        plant_collection.insert_one(
            {
                'plant_id': assigned_uuid,
                'plant_name': data.get('plant_name'),
                'plant_type': data.get('plant_type'),
                'plant_date': data.get('plant_date'),
                'plant_registered': data.get('plant_registered'),
                'plant_update_poll': data.get('plant_update_poll'),
                'update_poll_activated': data.get('update_poll_activated'),
                'device_mac': data.get('device_mac'),
                'soil_sens_num': data.get('soil_sens_num')
            }
        )
        return jsonify({ 'success': True, 'message': 'Added to DB' }), 200
    elif request.method == 'GET':
        if not request.data:
            print(f'[PLANT][GET] Plant list request')
            plants = list(plant_collection.find({}, {'_id': 0}))
            print(f'[PLANT][GET] {plants}\n')
            return jsonify(plants), 200
        else:
            data = request.json
            if data.get('plant_id'):
                plant_id = data.get("plant_id")
                # print(f'[PLANT][GET][ID] {plant_id}')
                found_plant = plant_collection.find_one({'plant_id': plant_id}, {'_id': 0})
                if found_plant:
                    return jsonify(found_plant), 200
                return "ID not Found!", 404
            else:
                return 'Not implemented yet\n', 501
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
        unix_timestamp = int(time.time()) # [TODO] Add Validation in case uuid already exists
        print(f'[PLANT_DATA][POST] Recieved Plant data')
        print("\tPlant_ID: " + data.get('plant_id'))
        print("\tSensor Number: " + data.get('sensor_num'))
        print("\tTimestamp: " + str(unix_timestamp))
        print("\tTemperature: " + data.get('temp'))
        print("\tRelative Humidity: " + data.get('rel_hum'))
        print("\tLux: " + data.get('lux'))
        print("\tMoisture ADC Value: " + data.get('moi_ana'))
        plant_data_collection.insert_one(
            {
                'plant_id': data.get('plant_id'),
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
        print(f'[PLANT_DATA][GET] Plant data list request')
        plant_data = list(plant_data_collection.find({}, {'_id': 0}))
        print(f'[PLANT_DATA][GET] {plant_data}\n')
        return jsonify(plant_data), 200
    elif request.method == 'DELETE':
        # [TODO]
        return 'Not implemented yet\n', 501
    else:
        return 'Not Found\n', 404


if __name__ == '__main__':
    scheduler.api_enabled = True
    scheduler.init_app(app)
    load_scheduler_jobs_at_startup()
    scheduler.start()
    app.run(debug=False, host=ip, port=2000, use_reloader=False)