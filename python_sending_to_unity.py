import serial
import socket

# Serial (STM32)
SERIAL_PORT = "COM3"
BAUD = 256000

# TCP
HOST = "127.0.0.1"
PORT = 5005

WRAP_THRESHOLD = 100
VALID_MAX_CM = 350 #cm


def decode_packet(packet):
    b0, b1, b2, b3, b4 = packet

    if b0 not in (0x3E, 0x02):
        return None

    angle_lsb = b1 >> 1
    raw_angle = (b2 << 7) | angle_lsb
    angle = raw_angle / 64.0

    raw_dist = (b4 << 8) | b3
    distance = raw_dist / 4.0
    distance = distance / 10.0  # cm

    return angle, distance


def main():
    ser = serial.Serial(SERIAL_PORT, BAUD, timeout=0)

    # TCP server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(1)

    print("Waiting for Unity to connect...")
    conn, addr = server.accept()
    print("Connected to Unity:", addr)

    buffer = bytearray()
    scan = []
    prev_angle = None

    while True:
        buffer.extend(ser.read(200))

        while len(buffer) >= 5:
            if buffer[0] not in (0x3E, 0x02):
                buffer.pop(0)
                continue

            packet = buffer[:5]
            buffer = buffer[5:]

            result = decode_packet(packet)
            if not result:
                continue

            angle, dist = result

            if dist <= 0 or dist > VALID_MAX_CM:
                continue

            # Detect full scan
            if prev_angle is not None and (prev_angle - angle) > WRAP_THRESHOLD:

                scan.sort(key=lambda x: x[0])

                # Send to Unity
                conn.sendall(b"<START>\n")

                for a, d in scan:
                    line = f"{a:.2f},{d:.2f}\n"
                    conn.sendall(line.encode())

                conn.sendall(b"<END>\n")

                scan = []

            scan.append((angle, dist))
            prev_angle = angle


if __name__ == "__main__":
    main()
