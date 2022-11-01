import multiprocessing
import random
import socket
import time
import io
import os

class MultiProcessingSocketLidarController(multiprocessing.Process):
    def __init__(self, host, port):
        multiprocessing.Process.__init__(self)
        
        self.requests = multiprocessing.Queue(maxsize=5)
        self.results = multiprocessing.Queue()
        self.connection_alive = multiprocessing.Value("i")
        self.connection_alive.value = False
        self.hosting_address = (host, int(port))

    def get_distance(self, direction=0):
        direction = float(direction)
        self.requests.put(("Distance", direction))
        return_direction, timestamp, distance = self.results.get()
        return (timestamp if return_direction == direction else None, distance)

    def set_motor_speed(self, speed):
        self.requests.put(("Speed", int(speed)))
    
    def connected(self):
        return bool(self.connection_alive.value)

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        print("LidarController server listening", self.hosting_address)
        sock.bind(self.hosting_address)
        sock.listen(0)

        client, addr = sock.accept()
        self.connection_alive.value = True
        print("Connected to Raspberry Pi, address: ", addr)

        try:

            while True:
                if not self.requests.empty():
                    req = self.requests.get(block=False)
                    if req[0] == "Distance":
                        direction = req[1]
                        client.send(b"\xa4"+direction.hex().encode())
                        msg = client.recvmsg(512)[0]

                        if not msg:
                            # self.connection_alive.value = False
                            # print("Lidar Connection broken")
                            # break
                            continue

                        # \xa4 + time_hex(21) + distance
                        br = io.BytesIO(msg)

                        if br.read(1) != b"\xa4":
                            print("Error: Invalid data format", msg)
                            break

                        time_stamp = float.fromhex(br.read(21).decode())
                        distance = int.from_bytes(br.read(), byteorder="big")

                        print("Got distances", time_stamp, distance)
                        self.results.put((direction, time_stamp, distance))

                    if req[0] == "Speed":
                        speed = req[1]
                        client.send(b"\xa5"+speed.to_bytes(1, byteorder="big"))
        finally:
            client.close()

if __name__ == '__main__':
    addr = os.getenv("HOST_ADDR", "127.0.0.1")
    port = os.getenv("HOST_LIDAR_P", 12394)

    controller = MultiProcessingSocketLidarController(addr, port)
    controller.start()

    while not controller.connected():
        time.sleep(0.1)
    
    print("Object connected")

    angle = random.choice([1, 50, 120])
    print(controller.get_distance(direction=angle))

    controller.set_motor_speed(12)