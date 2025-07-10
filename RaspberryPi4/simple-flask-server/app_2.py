#Simple Flask test program
# connect to 

import subprocess
from flask import Flask, request
from datetime import datetime

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import ConnectionFailure

app = Flask(__name__)

try:
    client = MongoClient("mongodb://dan:test@0.0.0.0:27017", server_api=ServerApi('1'))
    client.admin.command('ping')
except ConnectionFailure as e:
    print(f"Could not connect to mongoDB database {e}")

# Get current assigned IP using hostname command on Linux
y = subprocess.run(['/usr/bin/hostname', '-I'], capture_output=True)
ipAddrs = y.stdout.split()
ip = ipAddrs[0].decode("utf-8")

# Change to the IP of device running this app
# ip = '192.168.0.7' # Home IP 
# ip = '192.168.0.103' # Lab IP
@app.route('/')
@app.route('/index')
def index():
    return f"Raspberry Pi4 4G on {ip}\nAdd /hello for a surprise :)", 200

@app.route('/tick')
def hello():
    return f'Hello, the time is: {datetime.now()}', 200

@app.route('/tock', methods=['POST'])
# @app.route('/json_example', methods=['POST'])
def handle_json():
    data = request.json
    print(data.get('temp'))
    print(data.get('rel_hum'))
    print(data.get('lux'))
    print(data.get('moi_ana'))
    print(data.get('moi_percent'))
    return data


if __name__ == '__main__':
    app.run(debug=True, host=ip)