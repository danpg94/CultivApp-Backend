#Simple Flask test program
# connect to 

from flask import Flask, request
from datetime import datetime

app = Flask(__name__)

# Change to the IP of device running this app
# ip = '192.168.0.7' # Home IP 
ip = '192.168.0.103' # Lab IP
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