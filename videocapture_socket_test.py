import socket
import time
import cv2
import io

HOST = '127.0.0.1'
PORT = 5555
BUFFER_SIZE = 1024

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)

while True:
    im = cv2.imread("test.jpg")
    ret, encoded_img = cv2.imencode(".jpg", im, [cv2.IMWRITE_JPEG_QUALITY, 50])
    buffer_reader = io.BytesIO(encoded_img.tobytes())

    head = b"START" + time.time().hex().encode()
    s.sendto(head, (HOST, PORT))
    while True:
        b = buffer_reader.read(BUFFER_SIZE)
        if not b:
            break
        s.sendto(b, (HOST, PORT))
    s.sendto(b"END", (HOST, PORT))

    time.sleep(0.01)