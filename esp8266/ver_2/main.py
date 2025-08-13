import network
import socket
import utime
import urequests as request

ssid = 'IZZI-37B9'
pswd = '98F781F737B9'
esp_board_name = 'ESP8266_1'

HTTP_HEADERS = {'Content-Type': 'application/json'}

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
            response = request.post(url='http://192.168.0.6:2000/device', json = data, headers = HTTP_HEADERS)
            if response.status_code == 200:
                print(response.text)
                send_dev_name = True
        except:
            print('Error connecting: retrying in 10 s')
            utime.sleep(10)

do_connect()

while (1):
    print("Connected")
    utime.sleep(10)
