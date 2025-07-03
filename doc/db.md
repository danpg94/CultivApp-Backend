Collection

sensor_device:
    device_name:    (Ex. ESP8266_01)
    device_type:    (Ex. ESP32, ES8266, Raspberry Pi Pico, etc)
    plant_id:       (Ex. Cherry_Tomato_01)

heartbeat:
    device_name:    (Ex. ESP8266_01)
    timestamp:      (Ex. 2025-07-02T14:30:00Z)
    status:         (Online | Offline)

esp_images:
    timestamp:      (Ex. 2025-07-02T14:30:00Z)
    device_name:    (Ex. ESP8266_01)
    type:           (HIV sensor | manual | automatic)
    blob:           (compressed image binary)

phone_images:
    timestamp:      (Ex. 2025-07-02T14:30:00Z)
    type:           (Leaf_status | ?)
    blob:           (compressed image binary)


sensor data:
    plant_id:       (Ex. Cherry_Tomato_01)
    temp:           (Ex. 25.0 )
    rel_hum:        (Ex. 100%)
    lux:            (Ex. 1034)
    moi_ana:        (Ex. 432)
    moi_percent:    (Ex. 67.23%)
    timestamp:      (Ex. 2025-07-02T14:30:00Z)