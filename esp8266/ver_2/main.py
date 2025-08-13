import network
import socket
import utime
import urequests as request

ssid = 'IZZI-37B9'
pswd = '98F781F737B9'
esp_board_name = 'ESP8266_1'

HTTP_HEADERS = {'Content-Type': 'application/json'}

def do_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(ssid, pswd)
        while not wlan.isconnected():
            pass
    print('network config:', wlan.ipconfig('addr4'))
    data = dict()
    data['dev_name'] = esp_board_name
    data['session_ip'] = wlan.ipconfig('addr4')
    
    send_dev_name = False
    while not (send_dev_name):
        try:
            response = request.post(url='http://192.168.0.6:2000/device', json = data, headers = HTTP_HEADERS)
            if response.status_code == 200:
                print(response.text)
                send_dev_name = True
        except:
            print('Error connecting: retrying in 10 s')
            utime.sleep(10)

def setup_socket():
    # Create a socket and bind it to port 80
    addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
    s = socket.socket()
    s.bind(addr)
    s.listen(3) # Max 3 pending connections
    print('Listening on', addr)
    return s

def handle_request(client_socket):
    request = client_socket.recv(1024).decode()
    print('Request:', request)

    # Simple routing based on URL path
    if 'GET /data' in request:
        response = 'HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nSending Data... [done]\n'
    else:
        response = 'HTTP/1.1 404 Not Found\r\nContent-Type: text/plain\r\n\r\nNot Found\n'
    print(response)
    client_socket.send(response.encode())
    client_socket.close()


do_connect()
listening_socket = setup_socket()

while True:
    conn, addr = listening_socket.accept()
    print('Got a connection from %s:%d' % (addr[0], addr[1]))
    handle_request(conn)
