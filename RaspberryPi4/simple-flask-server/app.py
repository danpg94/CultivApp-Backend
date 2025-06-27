#Simple Flask test program
# connect to 

from flask import Flask

app = Flask(__name__)

# Change to the IP of device running this app 
ip = '192.168.0.7'

@app.route('/')
@app.route('/index')
def index():
    return f"Raspberry Pi4 4G on {ip}\nAdd /hello for a surprise :)", 200

@app.route('/hello')
def hello():
    return 'Hello World :^)', 200

if __name__ == '__main__':
    app.run(debug=True, host=ip)