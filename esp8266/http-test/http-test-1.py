import network
import utime
import urequests as request

HTTP_HEADERS = {'Content-Type': 'application/json'} 

def do_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect('TP-Link_5AEA', '55329484')
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())

do_connect()

while (1):
    response = request.get(url='http://192.168.0.103:5000/hello')
    if response.status_code == 200:
        print(response.text)
    utime.sleep(5)