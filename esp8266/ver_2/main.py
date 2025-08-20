import network
import socket
import utime
import ujson as json
import ahtx0
from machine import Pin, SoftI2C, ADC
from bh1750 import BH1750
import ubinascii
import urequests as request
from private_variables import ssid_priv, pswd_priv, server_url_priv # Remember to have a file with the sensitive data loaded in the device 

######## Global Variables ########
ssid = ssid_priv
pswd = pswd_priv
MAX_HUM_SENSORS = 8
device_board_type = 'ESP8266'
server_url = server_url_priv

######## Board Configuration #######
onboard_led = Pin(2, Pin.OUT)
onboard_led.value(0)

i2c = SoftI2C(scl=Pin(5), sda=Pin(4), freq=400000)

AHT10_enabled = True
BH1750_enabled = True

try:
    temp_sensor = ahtx0.AHT10(i2c)
except OSError:
    AHT10_enabled = False
try:
    light_sensor = BH1750(bus=i2c, addr=0x23)
except OSError:
    BH1750_enabled = False

adc = ADC(0)

pinA = Pin(12, Pin.OUT)
pinB = Pin(13, Pin.OUT)
pinC = Pin(14, Pin.OUT)

######## Functions ########
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f'[ LOG ] Attemptinng to connect to network {ssid}...')
        wlan.connect(ssid, pswd)
        while not wlan.isconnected():
            pass
    assigned_ip = wlan.ipconfig('addr4')[0]
    print('[ LOG ] Connection Successful! Network config:', {assigned_ip})
    # Get the raw MAC address as a bytes object
    mac_bytes = wlan.config('mac')
    # Convert the bytes object to a hexadecimal string and format it with colons
    mac_address = ubinascii.hexlify(mac_bytes, ':').decode().upper()
    
    return assigned_ip, mac_address

def health_check(assigned_ip, mac_address):
    data = dict()
    data['dev_type'] = device_board_type
    data['dev_mac_addr'] = mac_address
    data['session_ip'] = assigned_ip
    data['sensors_detected'] = check_sensors()

    send_health_check = False
    # send_health_check = True
    # [TODO]: Move connection to server to a different function
    while not (send_health_check):
        utime.sleep(5)
        print(f'[ LOG ] Attempting to connect to server on {server_url}')
        try:
            response = request.post(url=f'{server_url}', json = data, headers = {'Content-Type': 'application/json'})
            if response.status_code == 200:
                print(f'[ OK ] Response from server: {response.text}')
                send_health_check = True
        except:
            print(f'[ ERROR ] Error connecting to server: retrying in 10 s')
            onboard_led.value(0)
            utime.sleep(0.4)
            onboard_led.value(1)
            utime.sleep(10)

def setMultiplexerPins(a, b, c):
    pinA.value(a)
    pinB.value(b)
    pinC.value(c)

def check_sensors():
    print('[ LOG ] Checking sensors:')
    sensors = dict()
    sensors['temp_hum_sens'] = AHT10_enabled
    if AHT10_enabled:
        print(f'[ OK ] AHT10 Sensor detected')
    else:
        print(f'[WARN] AHT10 Sensor not detected!')
    
    sensors['light_sens'] = BH1750_enabled
    if BH1750_enabled:
        print(f'[ OK ] BH1750 Sensor detected')
    else:
        print(f'[WARN] BH1750 Sensor not detected!')

    print(f'[LOG] Soil Sensor Check:')
    for i in range(0,MAX_HUM_SENSORS):
        args = list("{0:03b}".format(i)) 
        setMultiplexerPins(int(args[2]), int(args[1]), int(args[0]))
        sensorAnalog = adc.read()
        if sensorAnalog > 50:
            print(f'\t[ OK ] Sensor{i}: OK')
            sensors[f'soil_sens_{i}']=True
        else:
            print(f'\t[WARN] Sensor{i}: NOT CONNECTED')
            sensors[f'soil_sens_{i}']=False
    return sensors

def setup_socket():
    # Create a socket and bind it to port 80
    print('[ LOG ] Creating socket')
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(3) # Max 3 pending connections
    print(f'[ OK ] Listening on: {addr}')
    return s



def get_sensor_data(mux_select):
    data = dict()

    # [TODO]: Add better handling of errors if a sensor disconnects after boot and implement a health_check call
    if BH1750_enabled:
        lux = light_sensor.luminance(BH1750.CONT_HIRES_1)
        data['lux'] = str("{:.2f}".format(lux))
    else:
        data['lux'] = "N/A"

    # [TODO]: Add better handling of errors if a sensor disconnects after boot and implement a health_check call
    if AHT10_enabled:
        temp = temp_sensor.temperature
        rel_hum = temp_sensor.relative_humidity
        data['temp'] = str("{:.2f}".format(temp))
        data['rel_hum'] = str("{:.2f}".format(rel_hum))
    else:
        data['temp'] = "N/A"
        data['rel_hum'] = "N/A"

    args = list("{0:03b}".format(mux_select)) # Convert sensor number to binary in order to set sensor input of multiplexer
    setMultiplexerPins(int(args[2]), int(args[1]), int(args[0]))
    sensorAnalog = adc.read()

    #print("\nSensor Number: {}".format(mux_select))
    #print("Temperature: {:.2f} C".format(temp))
    #print("Humidity: {:.2f}".format(rel_hum))
    #print("Luminance: {:.2f} lux".format(lux))
    #print("Soil Moisture ADC Value: {:.2f}".format(sensorAnalog))
    
    data['sensor_num'] = str(mux_select)
    data['moi_ana'] = str("{:.2f}".format(sensorAnalog))
    return data

def handle_request(client_socket):
    try:
        request = client_socket.recv(1024).decode()
        # print('Request:', request)
        header_end = request.find("\r\n\r\n")
        if header_end != -1:
            json_payload_bytes = request[header_end + 4:]
        else:
            json_payload_bytes = request
        # Simple routing based on URL path
        # print(f"Payload Bytes: {len(json_payload_bytes)}\n")
        if 'POST /data' in request:
            json_data_recieved = json.loads(json_payload_bytes)
            # print(json_data_recieved)
            data_to_send = get_sensor_data(int(json_data_recieved['sensor_num']))
            json_string = json.dumps(data_to_send)
            print(f'[ OK ] Sending data to server')
            response = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n'.encode('utf-8') +  json_string.encode('utf-8')
        elif 'GET /ping' in request:
            data = dict()
            data['status'] = 'OK'
            json_string = json.dumps(data)
            print(f'[ OK ] Recieved PING request from server')
            response = 'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n'.encode('utf-8') +  json_string.encode('utf-8')
        else:
            print(f'[WARN] Request not supported. Returning 404')
            response = 'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot Found\n'.encode()
    except Exception as e:
        print(f'[ERROR] An unexpected error occured. Type: {type(e)} Error:{e}')
        response = f'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nError: {type(e)}, {e} \n'.encode()
    print(f'[LOG] Response to server: \n{response}\n')
    client_socket.send(response)
    client_socket.close()




###### Main "Function" ######
assigned_ip, mac_address = connect_wifi()
health_check(assigned_ip, mac_address)
listening_socket = setup_socket()

while True:
    onboard_led.value(1)
    conn, addr = listening_socket.accept()
    onboard_led.value(0)
    print(f'[ LOG ] Got a connection from {addr[0]}:{addr[1]}')
    handle_request(conn)
