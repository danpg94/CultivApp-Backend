/assign POST (rbpi)
ESP8266 first request to RBPi
    ip: 
    device_name:
    device_type:

/heartbeat POST (rbpi)
Ack ESP8266 is online and wait for orders:
    ack: OK

/sensor POST (rbpi)
ESP8266 send sensor data to RBPi
    temp:
    rel_hum:
    lux:
    plant_id:
    moi_ana:
    moi_percent:

/request (8266)
RBPi request for sensor info:
    plant_id:



/image (rbpi)
ESP32 send image to RBPi
    device_name:    (Ex. ESP8266_01)
    type:           (HIV sensor | manual | automatic)
    blob:           (compressed image binary)