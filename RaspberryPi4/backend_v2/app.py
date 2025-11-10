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

# Schema for device
# [TODO]: Change names of fields to avoid confusion
device_registration_schema = {
    "required": ["dev_type", "dev_mac_addr", "session_ip", "sensors_detected"]

}

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

# Schema for plant registration data
plant_registration_schema = {
    "required": ["plant_name", "plant_type", "plant_date", "plant_update_poll", "device_mac", "soil_sens_num"],
    "properties": {
        "plant_name": {"type": 'string'},
        "plant_type": {"type": 'string'},
        "plant_date": {"type": 'integer'},
        "plant_update_poll": {"type": 'integer'},
        "update_poll_activated": {"type": 'boolean'},
        "device_mac": {"type": 'string'},
        "soil_sens_num": {"type": 'integer'}
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

def update_scheduler_job(plant_id, device_mac, interval, soil_sens_num, reason=""):
    """Función auxiliar para actualizar el job del scheduler"""
    device = device_collection.find_one({'mac': device_mac})
    if device is None:
        print(f'\t[WARNING] Device {device_mac} not found in database, scheduler job not updated')
        return False
    
    if not curl_ping_device(device['latest_ip']):
        print(f'\t[WARNING] Device {device_mac} is not reachable, scheduler job not updated')
        return False
    
    try:
        scheduler.remove_job(plant_id)
    except:
        pass  # El job puede no existir
    
    job_id = scheduler.add_job(
        id=f'{plant_id}',
        func=curl_post_device,
        args=[plant_id, device['latest_ip'], soil_sens_num],
        trigger="interval",
        seconds=interval
    )
    print(f'\t[LOG] Updated scheduler job for {plant_id} (interval: {interval}s, sensor: {soil_sens_num}){f" - {reason}" if reason else ""}')
    return True

def load_request_jobs(plants_entry):
    for plant in plants_entry:
        device = device_collection.find_one({'mac': plant['device_mac']})
        if device is not None:
            if curl_ping_device(device['latest_ip']):
                print(f'[LOG] Pinging {plant["plant_name"]} on {device["latest_ip"]}')
                job_id = scheduler.add_job(id=f'{plant["plant_id"]}' ,func=curl_post_device, args=[plant['plant_id'],device['latest_ip'], plant['soil_sens_num']], trigger="interval", seconds=plant['plant_update_poll'])
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
        data = request.json
        device_entry = device_collection.find_one({"mac": data["dev_mac_addr"]})
        if device_entry == None:
            print(f'[NEW DEVICE] New {data["dev_type"]} Device detected with MAC: {data["dev_mac_addr"]} on {data["session_ip"]}')
            device_collection.insert_one(
                {
                    "name": data["dev_type"], 
                    "mac": data["dev_mac_addr"], 
                    "latest_ip": data["session_ip"], 
                    "sensor_list": data["sensors_detected"]
                }
            )
            return 'Device added successfuly\n', 200
        return 'Error: No information sent', 404 
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

@app.route('/plant/<plant_id>', methods=['POST', 'UPDATE', 'DELETE', 'GET'])
def single_plant_handler(plant_id):
    if request.method == 'GET':
        # data = request.json
        # plant_id = data.get("plant_id")
        print(f'[PLANT][GET][ID] Plant request {plant_id}')
        found_plant = plant_collection.find_one({'plant_id': plant_id}, {'_id': 0})
        if found_plant:
            return jsonify(found_plant), 200
        return "ID not Found!\n", 404
    return 'Not implemented yet\n', 501


@app.route('/plant', methods=['POST', 'UPDATE', 'DELETE', 'GET', 'PUT']) 
def plant_handler():
    if request.method == 'POST':
        # Validar schema solo para POST
        try:
            schema.validate(request.json, plant_registration_schema)
        except JsonValidationError as e:
            return jsonify({'error': e.message, 'errors': [validation_error.message for validation_error in e.errors]}), 406
        data = request.json
        assigned_uuid = str(uuid.uuid4()).split('-')[0] # [TODO] Add Validation in case uuid already exists
        date_registered = int(time.time())
        print(f'[PLANT][POST] Recieved new Plant')
        print(f"\tUUID: {assigned_uuid}")
        print(f"\tPlant Name: {data.get('plant_name')}")
        print(f"\tPlant Type: {data.get('plant_type')}")
        print(f"\tDate Planted: {data.get('plant_date')}")
        print(f"\tDate Registered: {date_registered}")
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
                'plant_registered': date_registered,
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
                print(f'[PLANT][GET][ID] Plant request {plant_id}')
                found_plant = plant_collection.find_one({'plant_id': plant_id}, {'_id': 0})
                if found_plant:
                    return jsonify(found_plant), 200
                return "ID not Found!\n", 404
            else:
                return 'Not implemented yet\n', 501
    elif request.method == 'DELETE':
        if request.data:
            data = request.json
            if data.get('plant_id'):
                plant_id = data.get('plant_id')
                print(f'[PLANT][DELETE][ID] Delete Plant: {plant_id}')
                deleted_plant = plant_collection.delete_one({'plant_id': plant_id})
                if deleted_plant.deleted_count:
                    return f'Plant {plant_id} Deleted Successfully\n', 200
                return f'Plant {plant_id} NOT Found!\n', 404
        return 'Error: No ID provided\n', 404

    elif request.method == 'UPDATE' or request.method == 'PUT':
        if not request.data:
            return jsonify({'success': False, 'message': 'Error: No data provided'}), 400
        
        data = request.json
        if not data.get('plant_id'):
            return jsonify({'success': False, 'message': 'Error: No plant_id provided'}), 400
        
        plant_id = data.get('plant_id')
        found_plant = plant_collection.find_one({'plant_id': plant_id}, {'_id': 0})
        if not found_plant:
            return jsonify({'success': False, 'message': 'Plant ID not found'}), 404
        
        print(f'[PLANT][UPDATE][ID] Update Plant: {plant_id}')
        
        # Campos no editables
        if 'plant_id' in data:
            print(f'\t[WARNING] plant_id cannot be modified, ignoring')
        if 'plant_registered' in data:
            print(f'\t[WARNING] plant_registered cannot be modified, ignoring')
        if data.get('device_mac') is not None:
            print(f'\t[WARNING] device_mac cannot be modified, ignoring')
        
        # Construir diccionario de actualización
        update_fields = {}
        editable_fields = ['plant_name', 'plant_type', 'plant_date', 'plant_update_poll', 'update_poll_activated', 'soil_sens_num']
        
        for field in editable_fields:
            if data.get(field) is not None:
                update_fields[field] = data.get(field)
                print(f'\t{field.replace("_", " ").title()}: {data.get(field)}')
        
        # Manejar actualización del scheduler si es necesario
        device_mac = found_plant.get('device_mac')
        update_poll_activated = data.get('update_poll_activated') if data.get('update_poll_activated') is not None else found_plant.get('update_poll_activated', False)
        plant_update_poll = data.get('plant_update_poll') if data.get('plant_update_poll') is not None else found_plant.get('plant_update_poll')
        soil_sens_num = data.get('soil_sens_num') if data.get('soil_sens_num') is not None else found_plant.get('soil_sens_num', 1)
        
        # Si se desactiva el polling, remover el job
        if data.get('update_poll_activated') is not None and not update_poll_activated:
            try:
                scheduler.remove_job(plant_id)
                print(f'\t[LOG] Removed scheduler job for {plant_id} (polling deactivated)')
            except:
                pass
        # Si se actualiza intervalo, sensor, o se activa polling, actualizar scheduler
        elif (data.get('plant_update_poll') is not None or data.get('soil_sens_num') is not None or 
              (data.get('update_poll_activated') is not None and update_poll_activated)) and update_poll_activated and plant_update_poll:
            update_scheduler_job(plant_id, device_mac, plant_update_poll, soil_sens_num)
        
        # Actualizar en la base de datos
        if update_fields:
            result = plant_collection.update_one({'plant_id': plant_id}, {'$set': update_fields})
            if result.modified_count > 0:
                print(f'[PLANT][UPDATE][ID] Plant {plant_id} updated successfully')
                return jsonify({'success': True, 'message': f'Plant {plant_id} updated successfully'}), 200
            else:
                return jsonify({'success': False, 'message': 'No changes were made'}), 200
        else:
            return jsonify({'success': False, 'message': 'No valid fields provided for update'}), 400


    else:
        return 'Not implemented\n', 501

@app.route('/plant_data/<plant_id>', methods=['POST', 'GET', 'DELETE'])
def single_plant_data_handler(plant_id):
    if request.method == 'GET':
        # data = request.json 
        # plant_id = data.get('plant_id')
        #if data.get('dates'):
        #    # [TODO]: implement a date query method
        #    return 'Not implemented yet', 501
        print(f'[PLANT_DATA][GET] Plant: {plant_id} data request')
        plant_data = list(plant_data_collection.find({'plant_id': plant_id}, {'_id': 0}))
        print(f'[PLANT_DATA][GET] Sending plant_id {plant_id} records: {len(plant_data)}\n')
        # print(plant_data)
        if not any(plant_data):
            return 'Error: Plant ID Not Found\n', 404
    return jsonify(plant_data), 200


@app.route('/plant_data', methods=['POST', 'GET', 'DELETE'])
@schema.validate(ESP8266_sensor_data_schema)
def plant_data_handler():
    if request.method == 'POST':
        data = request.json
        unix_timestamp = int(time.time())
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
        if not request.data:
            print(f'[PLANT_DATA][GET] All Plant data list request')
            plant_data = list(plant_data_collection.find({}, {'_id': 0}))
            print(f'[PLANT_DATA][GET] Total Plant data sent: {len(plant_data)}\n')
            return jsonify(plant_data), 200
        else:
            data = request.json 
            if data.get('plant_id'):
                plant_id = data.get('plant_id')
                if data.get('dates'):
                    # [TODO]: implement a date query method
                    return 'Not implemented yet', 501
                print(f'[PLANT_DATA][GET] Plant: {plant_id} data request')
                plant_data = list(plant_data_collection.find({'plant_id': plant_id}, {'_id': 0}))
                # print(plant_data)
                if not any(plant_data):
                    return 'Error: Plant ID Not Found\n', 404
                return jsonify(plant_data), 200
            else:
                return 'Error: Plant ID not provided\n', 404
    elif request.method == 'DELETE':
        if request.data:
            data = request.json
            if data.get('plant_id'):
                plant_id = data.get('plant_id')
                deleted_plant_data = plant_data_collection.delete_many({'plant_id': plant_id})
                if deleted_plant_data.deleted_count:
                    return f'Plant data from plant id {plant_id} Deleted Successfully\n', 200
                return f'Plant data from plant ID {plant_id} NOT found\n', 404
        return 'Error: No ID provided\n', 404
    else:
        return 'Not Found\n', 404


if __name__ == '__main__':
    scheduler.api_enabled = True
    scheduler.init_app(app)
    load_scheduler_jobs_at_startup()
    scheduler.start()
    app.run(debug=False, host=ip, port=2000, use_reloader=False)