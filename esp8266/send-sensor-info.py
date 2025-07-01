import network
import utime
import urequests as request

from machine import Pin, SoftI2C, ADC

import ahtx0
from bh1750 import BH1750

ssid = 'TP-Link_5AEA'
pswd = '55329484'

i2c = SoftI2C(scl=Pin(5), sda=Pin(4), freq=400000)
temp_sensor = ahtx0.AHT10(i2c)
# BH1750 ADDR pin set to GND, therefore addr=0x23
light_sensor = BH1750(bus=i2c, addr=0x23)

adc = ADC(0)

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
    
def sensor_data():
    data = dict()
    lux = light_sensor.luminance(BH1750.CONT_HIRES_1)
    print("\nTemperature: %0.2f C" % temp_sensor.temperature)
    data['temp'] = temp_sensor.temperature
    print("Humidity: %0.2f %%" % temp_sensor.relative_humidity)
    data['rel_hum'] = temp_sensor.relative_humidity
    print("Luminance: {:.2f} lux".format(lux))
    data['lux'] = lux
    sensorPercent = 0

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
    data['moi_ana'] = sensorAnalog
    data['moi_percent'] = sensorPercent
    return data

do_connect()

while (1):
    response = request.get(url='http://192.168.0.103:5000/tick')
    if response.status_code == 200:
        print(response.text)
    data = sensor_data()
    req = request.post('http://192.168.0.103:5000/tock', json = data, headers = HTTP_HEADERS ) 
    req.close()
    utime.sleep(5)


