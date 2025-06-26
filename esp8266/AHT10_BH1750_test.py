import utime
from machine import Pin, SoftI2C

import ahtx0
from bh1750 import BH1750

i2c = SoftI2C(scl=Pin(5), sda=Pin(4), freq=400000)

temp_sensor = ahtx0.AHT10(i2c)
# BH1750 ADDR pin set to GND, therefore addr=0x23
light_sensor = BH1750(bus=i2c, addr=0x23)

while True:
    lux = light_sensor.luminance(BH1750.CONT_HIRES_1)
    print("\nTemperature: %0.2f C" % temp_sensor.temperature)
    print("Humidity: %0.2f %%" % temp_sensor.relative_humidity)
    print("Luminance: {:.2f} lux".format(lux))
    utime.sleep(5)