import utime
from machine import Pin, SoftI2C

import ahtx0

i2c = SoftI2C(scl=Pin(5), sda=Pin(4))

sensor = ahtx0.AHT10(i2c)

while True:
    
    print("\nTemperature: %0.2f C" % sensor.temperature)
    print("Humidity: %0.2f %%" % sensor.relative_humidity)
    utime.sleep(5)