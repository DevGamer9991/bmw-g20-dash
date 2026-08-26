import socket
import struct
import time
import threading
from flask import Flask, render_template
from flask_socketio import SocketIO

AGENT_IP = "192.168.0.11"
AGENT_PORT = 6801
SRC_ADDR = 0xF4
DST_ADDR = 0x12

app = Flask(__name__)
# async_mode='threading' keeps it compatible with your standard socket logic
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

def send_hsfz_command(sock, uds_payload):
    body = bytes([SRC_ADDR, DST_ADDR]) + uds_payload
    length = len(body)
    hsfz_frame = struct.pack(">IH", length, 0x0001) + body
    sock.sendall(hsfz_frame)

def read_hsfz_response(sock, timeout=1.0):
    sock.settimeout(timeout)
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        header_raw = sock.recv(6)
        if len(header_raw) < 6:
            continue
        length, msg_type = struct.unpack(">IH", header_raw)
        
        body = b""
        while len(body) < length:
            chunk = sock.recv(length - len(body))
            if not chunk:
                break
            body += chunk
            
        if len(body) < length:
            continue
        if msg_type == 0x0002:
            continue
        if msg_type == 0x0001 and len(body) >= 2:
            src, dst = body[0], body[1]
            if src == DST_ADDR and dst == SRC_ADDR:
                return body[2:]
    return b""

def car_polling_thread():
    """Background thread that connects to ENET and streams data."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print(f"[*] Connecting to {AGENT_IP}:{AGENT_PORT}...")
        sock.connect((AGENT_IP, AGENT_PORT))
        print("[+] Connected!")

        send_hsfz_command(sock, bytes.fromhex("2C 03 F3 00"))
        read_hsfz_response(sock)

        map_payload = bytes.fromhex("2C 01 F3 00 48 07 01 02")
        send_hsfz_command(sock, map_payload)
        read_hsfz_response(sock)

        read_payload = bytes.fromhex("22 F3 00")

        while True:
            send_hsfz_command(sock, read_payload)
            uds_resp = read_hsfz_response(sock)
            
            if uds_resp.startswith(b"b\xf3\x00"):
                data = uds_resp[3:5]
                raw_rpm = struct.unpack(">H", data)[0]
                rpm = raw_rpm * 0.5
                
                # Push data to the webpage
                socketio.emit('rpm_data', {'rpm': rpm})

            time.sleep(0.05)
            
    except Exception as e:
        print(f"[!] Error: {e}")
        # Try to reconnect after a delay if connection drops
        time.sleep(5)
        car_polling_thread()
    finally:
        sock.close()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == "__main__":
    # Start the ENET polling in the background
    threading.Thread(target=car_polling_thread, daemon=True).start()
    # Run the web server
    socketio.run(app, host="0.0.0.0", port=8080)