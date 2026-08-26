import socket
import struct
import time

AGENT_IP = "192.168.0.11"  # Replace with ENET / Auto-Discovery IP
AGENT_PORT = 6801

SRC_ADDR = 0xF4  # PC Tester ID
DST_ADDR = 0x12  # DME ECU ID


def send_hsfz_command(sock: socket.socket, uds_payload: bytes):
    """Wraps UDS payload into HSFZ frame (Header: len + type 0x0001 + src/dst) and transmits."""
    body = bytes([SRC_ADDR, DST_ADDR]) + uds_payload
    length = len(body)
    # 4-byte Big-Endian length + 2-byte Type 0x0001
    hsfz_frame = struct.pack(">IH", length, 0x0001) + body
    
    # print(hsfz_frame)
    
    sock.sendall(hsfz_frame)


def read_hsfz_response(sock: socket.socket, timeout=1.0) -> bytes:
    """Reads HSFZ responses, filtering out ZGW Gateway Echo frames (Type 0x0002)."""
    sock.settimeout(timeout)
    start_time = time.time()

    while (time.time() - start_time) < timeout:
        # Read HSFZ 6-byte TCP prefix header (4 bytes length + 2 bytes type)
        header_raw = sock.recv(6)
        if len(header_raw) < 6:
            continue

        length, msg_type = struct.unpack(">IH", header_raw)

        # Read remaining body bytes (length bytes)
        body = b""
        while len(body) < length:
            chunk = sock.recv(length - len(body))
            if not chunk:
                break
            body += chunk

        if len(body) < length:
            continue

        # Ignore ZGW Gateway Echo Frames (Type 0x0002)
        if msg_type == 0x0002:
            continue

        # Verify Real ECU Data Frame (Type 0x0001 from ECU 0x12)
        if msg_type == 0x0001 and len(body) >= 2:
            src, dst = body[0], body[1]
            if src == DST_ADDR and dst == SRC_ADDR:
                return body[2:]  # Extract pure UDS payload

    return b""


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        print(f"[*] Connecting to BMW ENET interface at {AGENT_IP}:{AGENT_PORT}...")
        sock.connect((AGENT_IP, AGENT_PORT))
        print("[+] Connected!")

        # 1. Clear dynamic DID F300 (Service 2C Subfunction 03)
        print("[*] Clearing dynamic identifier F300...")
        send_hsfz_command(sock, bytes.fromhex("2C 03 F3 00"))
        resp = read_hsfz_response(sock)
        print(f"    Response: {resp.hex()}")

        # 2. Define Dynamic DID F300 with RPM (0x4807, 2 bytes) and Battery Voltage (0x5815, 2 bytes)
        # Payload: Service 2C 01 | DID F300 | DID 4807 Pos 01 Len 02 | DID 5815 Pos 02 Len 02
        print("[*] Mapping RPM (0x4807) and Voltage (0x5815) to F300...")
        map_payload = bytes.fromhex("2C 01 F3 00 48 07 01 02")
        send_hsfz_command(sock, map_payload)
        resp = read_hsfz_response(sock)
        print(f"    Response: {resp.hex()}")

        print("\n[+] Streaming sensor values (Ctrl+C to exit):\n")

        # 3. Read Dynamic DID F300 (Service 22 F3 00)
        read_payload = bytes.fromhex("22 F3 00")

        while True:
            send_hsfz_command(sock, read_payload)
            uds_resp = read_hsfz_response(sock)
            
            # print(uds_resp.startswith(b"b\xf3\x00"))

            # Check positive response to Service 0x22 (Header: 62 f3 00)
            if uds_resp.startswith(b"b\xf3\x00"):
                data = uds_resp[3:5]  # Pure payload data

                # RPM: Bytes 0-1 (Big-Endian uint16 * 0.5)
                raw_rpm = struct.unpack(">H", data)[0]
                rpm = raw_rpm * 0.5

                print(f"Engine Speed: {rpm:6.1f} RPM", end="\r")

            time.sleep(0.05)  # 20 Hz polling speed

    except KeyboardInterrupt:
        print("\n[*] Polling stopped.")
    except Exception as err:
        print(f"[!] Error: {err}")
    finally:
        sock.close()


if __name__ == "__main__":
    main()