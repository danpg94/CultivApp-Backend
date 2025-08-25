### Plant Insert Test ###
import requests, time

url = 'http://192.168.0.6:2000/plant'
mac_address = '84:F3:EB:96:DE:CC'
payload = {
    'plant_name': 'plant_1',
    'plant_type': 'Cherry Tomato',
    'plant_date': int(time.time()),
    'plant_registered': int(time.time()),
    'plant_update_poll': 10,
    'update_poll_activated': True,
    'device_mac': mac_address,
    'soil_sens_num': 0
}
res = requests.post(url, json=payload, headers={})
print(res)