import os
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
        
        # Oil Temp
        send_hsfz_command(sock, bytes.fromhex("2C 01 F3 00 44 02 01 02"))
        read_hsfz_response(sock)
        
        # Coolant Temp
        send_hsfz_command(sock, bytes.fromhex("2C 01 F3 00 43 00 01 02"))
        read_hsfz_response(sock)
        
        # Coolant Temp (Radiator Outlet)
        send_hsfz_command(sock, bytes.fromhex("2C 01 F3 00 4A 21 01 02"))
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
                
                oil_temp_raw = struct.unpack(">H", uds_resp[10:12])[0]
                oil_temp_c = round(oil_temp_raw * 0.0071948, 2)
                
                print("Oil Temp (C):", oil_temp_c)
                print("Oil Temp (Raw):", oil_temp_raw)
                
                oil_temp_f = (oil_temp_c * 9/5) + 32
                
                coolant_temp_raw = struct.unpack(">H", uds_resp[12:14])[0]
                coolant_temp_c = (coolant_temp_raw * 0.75) - 48
                
                # print("Coolant Temp (C):", coolant_temp_c)
                # print("Coolant Temp (Raw):", coolant_temp_raw)
                
                coolant_temp_rad_out_raw = struct.unpack(">H", uds_resp[14:16])[0]
                coolant_temp_rad_out_c = (coolant_temp_rad_out_raw * 0.75) - 48
                
                # print("Coolant Temp (Radiator Outlet) (C):", coolant_temp_rad_out_c)
                # print("Coolant Temp (Radiator Outlet) (Raw):", coolant_temp_rad_out_raw)

                socketio.emit('car_data', {'rpm': rpm, 'boost_pressure': boost_psi, 'intake_air_temp': round(intake_air_temp_f), 'oil_temp': round(oil_temp_f)})

            elif uds_resp.startswith(b"\x7F"):
                print(f"[-] ECU busy/NACK: {uds_resp.hex()}")

            time.sleep(0.1)
            
    except Exception as e:
        print(f"[!] Error: {e}")
        time.sleep(5)
        car_polling_thread()
    finally:
        sock.close()

@app.route("/socket.io.js")
def download_socket_io():
    return send_from_directory(directory="./templates", path="socket.io.js")

@app.route("/dashboard.js")
def download_dashboard_js():
    return send_from_directory(directory="./templates", path="dashboard.js")

@app.route("/menu.js")
def download_menu_js():
    return send_from_directory(directory="./templates", path="menu.js")

@app.route('/')
def index():
    return render_template('./pages/default-yellow.html')

@app.route('/menu')
def menu():
    # Define the path to your 'pages' folder
    pages_directory = os.path.join(app.root_path, 'templates/pages')
    pages_list = []
    
    # Check if the folder exists to prevent errors
    if os.path.exists(pages_directory):
        for filename in os.listdir(pages_directory):
            # Only process HTML files (adjust if your pages are .md, etc.)
            if filename.endswith('.html'):
                page_id = os.path.splitext(filename)[0]
                
                # Format for display: replace hyphens with spaces and capitalize
                display_name = page_id.replace('-', ' ').title()
                
                # Add to our list as a dictionary
                pages_list.append({
                    'id': page_id,
                    'name': display_name
                })
                
    # Sort alphabetically so the menu is organized
    pages_list.sort(key=lambda x: x['name'])
    
    # Pass the list to your HTML template
    return render_template('menu.html', pages=pages_list)

# take the /<path:filename> route and serve the html file from pages the directory
@app.route('/page/<path:filename>')
def serve_page(filename):
    return render_template(f'./pages/{filename}.html')

@app.route("/files/<path:filename>")
def download_font(filename):
    return send_from_directory(directory="./templates/static/", path=filename)

if __name__ == "__main__":
    threading.Thread(target=car_polling_thread, daemon=True).start()

    socketio.run(app, host="0.0.0.0", port=8080, allow_unsafe_werkzeug=True)