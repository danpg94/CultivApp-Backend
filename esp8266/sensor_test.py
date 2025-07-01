import utime
from machine import Pin, SoftI2C, ADC

import ahtx0
from bh1750 import BH1750

i2c = SoftI2C(scl=Pin(5), sda=Pin(4), freq=400000)

temp_sensor = ahtx0.AHT10(i2c)
# BH1750 ADDR pin set to GND, therefore addr=0x23
light_sensor = BH1750(bus=i2c, addr=0x23)

adc = ADC(0)

while True:
    lux = light_sensor.luminance(BH1750.CONT_HIRES_1)
    print("\nTemperature: %0.2f C" % temp_sensor.temperature)
    print("Humidity: %0.2f %%" % temp_sensor.relative_humidity)
    print("Luminance: {:.2f} lux".format(lux))
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

    utime.sleep(5)