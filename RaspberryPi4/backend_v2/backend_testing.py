### Plant Insert Test ###
import requests, time, random

url = 'http://192.168.0.6:2000/plant'
mac_address = '84:F3:EB:96:DE:CC'
for i in range(3):
    payload = {
        'plant_name': f'plant_{i+1}',
        'plant_type': 'Cherry Tomato',
        'plant_date': int(time.time()),
        'plant_update_poll': random.randint(5,20),
        'update_poll_activated': True,
        'device_mac': mac_address,
        'soil_sens_num': i
    }
    res = requests.post(url, json=payload, headers={})
    print(res)