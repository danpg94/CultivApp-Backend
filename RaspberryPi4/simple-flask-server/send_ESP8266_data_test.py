import requests, random, subprocess, argparse
from time import sleep

y = subprocess.run(['/usr/bin/hostname', '-I'], capture_output=True)
ipAddrs = y.stdout.split()
LOCAL_IP = ipAddrs[0].decode("utf-8")

parser = argparse.ArgumentParser(
    prog='ESP8266 Data Test',
    description='a simple test that simulates an ESP8266 sending plant data',
)
parser.add_argument('-a', '--IP', default=LOCAL_IP)
parser.add_argument('-c', '--count', default=3)
parser.add_argument('-s', '--sleep', default=1)

def send_info(ip):
    HTTP_HEADERS = {'Content-Type': 'application/json'}

    temp = str("{:.2f}".format(random.uniform(18, 36)))
    rel_hum =  str("{:.2f}".format(random.uniform(95, 100)))
    lux =  str(random.randint(0, 20000))
    moi_ana =  str(random.randint(200, 700))
    moi_percent =  str("{:.2f}".format(random.uniform(0, 100)))

    data = {"temp": temp,
            "rel_hum": rel_hum,
            "lux": lux,
            "moi_ana": moi_ana,
            "moi_percent": moi_percent
            }
    response = requests.post(f'http://{ip}:5000/tock', json=data, headers=HTTP_HEADERS)
    print(f"Sending data: {data}")
    print(f"Response: {response.status_code}\n")
    print(f"Info: {response.json()}")

if __name__ == "__main__":
    args = parser.parse_args()
    count = int(args.count)
    ip = args.IP
    slp_sec = int(args.sleep)
    print(f"Destination IP: {ip}")
    print(f"Number of POST Requests: {count}")
    for _ in range(count):
        send_info(ip)
        sleep(slp_sec)