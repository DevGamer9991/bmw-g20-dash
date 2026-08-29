import socket
import struct
import time
import threading
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO

AGENT_IP = "192.168.0.11"
AGENT_PORT = 6801
SRC_ADDR = 0xF4
DST_ADDR = 0x12

app = Flask(__name__)

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
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print(f"[*] Connecting to {AGENT_IP}:{AGENT_PORT}...")
        sock.connect((AGENT_IP, AGENT_PORT))
        print("[+] Connected!")

        # Clear previous
        send_hsfz_command(sock, bytes.fromhex("2C 03 F3 00"))
        read_hsfz_response(sock)

        # RPM 
        send_hsfz_command(sock, bytes.fromhex("2C 01 F3 00 48 07 01 02"))
        read_hsfz_response(sock)

        # Ambient Pressure 
        send_hsfz_command(sock, bytes.fromhex("2C 01 F3 00 42 01 01 02"))
        read_hsfz_response(sock)
        
        # Charged Air Pressure
        send_hsfz_command(sock, bytes.fromhex("2C 01 F3 00 42 05 01 02"))
        read_hsfz_response(sock)
        
        # Intake Air Temperature
        send_hsfz_command(sock, bytes.fromhex("2C 01 F3 00 58 1E 01 01"))
        read_hsfz_response(sock)

        read_payload = bytes.fromhex("22 F3 00")

        while True:
            send_hsfz_command(sock, read_payload)
            uds_resp = read_hsfz_response(sock)

            if uds_resp.startswith(b"b\xf3\x00"):
                rpm_raw = struct.unpack(">H", uds_resp[3:5])[0]
                rpm = rpm_raw * 0.5
                
                ambient_pressure_raw = struct.unpack(">H", uds_resp[5:7])[0]
                ambient_pressure_mbar = ambient_pressure_raw * 0.0390625
                
                charged_pressure_raw = struct.unpack(">H", uds_resp[7:9])[0]
                charged_pressure_mbar = charged_pressure_raw * 0.078125
                
                boost_pressure_mbar = charged_pressure_mbar - ambient_pressure_mbar
                
                boost_psi_raw = boost_pressure_mbar / 68.94757
                
                boost_psi = round(boost_psi_raw, 1)
                
                intake_air_temp_raw = uds_resp[9]
                intake_air_temp_c = (intake_air_temp_raw * 0.75) - 48
                
                intake_air_temp_f = (intake_air_temp_c * 9/5) + 32
                
                socketio.emit('car_data', {'rpm': rpm, 'boost_pressure': boost_psi, 'intake_air_temp': round(intake_air_temp_f)})

            elif uds_resp.startswith(b"\x7F"):
                print(f"[-] ECU busy/NACK: {uds_resp.hex()}")

            time.sleep(0.1)
            
    except Exception as e:
        print(f"[!] Error: {e}")
        time.sleep(5)
        car_polling_thread()
    finally:
        sock.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/gauge.min.js")
def download_gauge():
    return send_from_directory(directory="./templates", path="gauge.min.js")

@app.route("/socket.io.js")
def download_socket_io():
    return send_from_directory(directory="./templates", path="socket.io.js")

@app.route("/fonts/<path:filename>")
def download_font(filename):
    return send_from_directory(directory="./templates/static/", path=filename)

if __name__ == "__main__":
    threading.Thread(target=car_polling_thread, daemon=True).start()

    socketio.run(app, host="0.0.0.0", port=8080, allow_unsafe_werkzeug=True)