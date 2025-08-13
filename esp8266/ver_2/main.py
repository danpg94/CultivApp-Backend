import network
import socket
import utime
import json
import ahtx0
from machine import Pin, SoftI2C, ADC
from bh1750 import BH1750

import urequests as request

ssid = 'TP-Link_5AEA'
pswd = '55329484'
esp_board_name = 'ESP8266_1'

HTTP_HEADERS = {'Content-Type': 'application/json'}

i2c = SoftI2C(scl=Pin(5), sda=Pin(4), freq=400000)
temp_sensor = ahtx0.AHT10(i2c)
light_sensor = BH1750(bus=i2c, addr=0x23)

adc = ADC(0)

pinA = Pin(12, Pin.OUT)
pinB = Pin(13, Pin.OUT)
pinC = Pin(14, Pin.OUT)

def do_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(ssid, pswd)
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ipconfig('addr4'))
    data = dict()
    data['dev_name'] = esp_board_name
    data['session_ip'] = wlan.ipconfig('addr4')
    
    send_dev_name = False
    while not (send_dev_name):
        try:
            response = request.post(url='http://192.168.0.101:2000/device', json = data, headers = HTTP_HEADERS)
            if response.status_code == 200:
                print(response.text)
                send_dev_name = True
        except:
            print('Error connecting: retrying in 10 s')
            utime.sleep(10)

def setup_socket():
    # Create a socket and bind it to port 80
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(3) # Max 3 pending connections
    print('Listening on', addr)
    return s

def setMultiplexerPins(a, b, c):
    pinA.value(a)
    pinB.value(b)
    pinC.value(c)

def get_sensor_data(mux_select):
    data = dict()
    lux = light_sensor.luminance(BH1750.CONT_HIRES_1)
    temp = temp_sensor.temperature
    rel_hum = temp_sensor.relative_humidity
    args = list("{0:03b}".format(mux_select)) # Convert sensor number to binary in order to set sensor input of multiplexer
    setMultiplexerPins(int(args[2]), int(args[1]), int(args[0]))
    sensorAnalog = adc.read()
    
    print("\nSensor Number: {}".format(mux_select))
    print("Temperature: {:.2f} C".format(temp))
    print("Humidity: {:.2f}".format(rel_hum))
    print("Luminance: {:.2f} lux".format(lux))
    print("Soil Moisture ADC Value: {:.2f}".format(sensorAnalog))
    
    data['sensor_num'] = str(mux_select)
    data['temp'] = str("{:.2f}".format(temp_sensor.temperature))
    data['rel_hum'] = str("{:.2f}".format(temp_sensor.relative_humidity))
    data['lux'] = str("{:.2f}".format(lux))
    data['moi_ana'] = str("{:.2f}".format(sensorAnalog))
    return data

def handle_request(client_socket):
    request = client_socket.recv(1024).decode()
    print('Request:', request)

    # Simple routing based on URL path
    if 'GET /data' in request:
        data_to_send = get_sensor_data(2)
        json_string = json.dumps(data_to_send)
        response = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n'.encode('utf-8') +  json_string.encode('utf-8')
    else:
        response = 'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot Found\n'.encode()
    print(response)
    client_socket.send(response)
    client_socket.close()


do_connect()
listening_socket = setup_socket()

while True:
    conn, addr = listening_socket.accept()
    print('Got a connection from %s:%d' % (addr[0], addr[1]))
    handle_request(conn)
