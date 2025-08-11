import network
import utime
import urequests as request

from machine import Pin, SoftI2C, ADC

import ahtx0
from bh1750 import BH1750

ssid = 'IZZI-37B9'
pswd = '98F781F737B9'

i2c = SoftI2C(scl=Pin(5), sda=Pin(4), freq=400000)
temp_sensor = ahtx0.AHT10(i2c)
# BH1750 ADDR pin set to GND, therefore addr=0x23
light_sensor = BH1750(bus=i2c, addr=0x23)

adc = ADC(0)

pinA = Pin(12, Pin.OUT)
pinB = Pin(13, Pin.OUT)
pinC = Pin(14, Pin.OUT)


def setMultiplexerPins(a, b, c):
    pinA.value(a)
    pinB.value(b)
    pinC.value(c)

HTTP_HEADERS = {'Content-Type': 'application/json'}

def do_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(ssid, pswd)
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ifconfig())
    
def sensor_data(mux_select):
    data = dict()
    lux = light_sensor.luminance(BH1750.CONT_HIRES_1)
    print("\nTemperature: {:.2f} C".format(temp_sensor.temperature))
    print("Humidity: {:.2f}".format(temp_sensor.relative_humidity))
    print("Luminance: {:.2f} lux".format(lux))
    data['temp'] = str("{:.2f}".format(temp_sensor.temperature))
    data['rel_hum'] = str("{:.2f}".format(temp_sensor.relative_humidity))
    data['lux'] = str("{:.2f}".format(lux))
    sensorPercent = 0

    # Convert sensor number to binary in order to set sensor input of multiplexer
    args = list("{0:03b}".format(mux_select))
    setMultiplexerPins(int(args[0]), int(args[1]), int(args[2]))

    sensorAnalog = adc.read()
    if sensorAnalog >= 50:
        wetPlant = 250 # water 200
        dryPlant = 500 # air 700
        sensorPercent = int((1 - (sensorAnalog - wetPlant) / (dryPlant - wetPlant)) * 100)

        if sensorPercent > 100:
            sensorPercent = 100
        elif sensorPercent < 0:
            sensorPercent = 0

    print("Soil Moisture Value: {:.2f}".format(sensorAnalog))
    print("Soil Moisture Percent: {:.2}".format(sensorPercent))
    data['moi_ana'] = str("{:.2f}".format(sensorAnalog))
    data['moi_percent'] = str("{:.2f}".format(sensorPercent))
    data['sensor_num'] = str(mux_select) 
    return data

do_connect()

while (1):
    # response = request.get(url='http://192.168.0.6:5000/tick')
    # if response.status_code == 200:
    #     print(response.text)
    i = 0
    while i < 8:
        data = sensor_data()
        req = request.post('http://192.168.0.6:5000/tock', json = data, headers = HTTP_HEADERS ) 
        req.close()
        utime.sleep(30)


