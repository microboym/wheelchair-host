import multiprocessing
from multiprocessing import shared_memory
import socket
import cv2
import os
import numpy as np

class MultiProcessingSocketVideoCapture(multiprocessing.Process):

    def __init__(self, frame_shape, ip_address, port):
        multiprocessing.Process.__init__(self)

        self.shape = np.array(frame_shape)
        self.host = ip_address
        self.port = int(port)
        self.socket_buffer_size = 1024
        
        self.img_buffer_size = self.shape.prod() * 2 + 256
        self.shm = shared_memory.SharedMemory(
            create=True, size=self.img_buffer_size)

        self.alive = multiprocessing.Value("i")
        self.alive.value = False
        self.current_frame = np.ndarray(
            self.shape, dtype=np.uint8, buffer=self.shm.buf)
        
    def __decode_img(self, buf):
        encoded_img = np.frombuffer(buf, dtype=np.uint8)
        img = cv2.imdecode(encoded_img, cv2.IMREAD_COLOR)
        if (img is not None) and (not img.any()):
            print("Error decoding image data")
            return None
        return img

    def serve(self, timeout=None):
        shm_img = np.ndarray(self.shape, dtype=np.uint8, buffer=self.shm.buf)
        flag = True

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            if timeout is not None:
                sock.settimeout(timeout)
            sock.bind((self.host, self.port))
            print("VideoCapture server listening on %s:%d" % (self.host, self.port))

            buffer = b''
            while True:
                data = sock.recvmsg(self.socket_buffer_size)
                if data[0][:5] == b"START":
                    buffer = b''
                    timestamp = float.fromhex(data[0][5:].decode())
                    ## TODO return the timestamp
                elif data[0] == b"END":
                    img = self.__decode_img(buffer)
                    if (img is not None) and img.any():
                        shm_img[:] = img[:]
                        self.alive.value = True
                else:
                    buffer += data[0]
        except socket.timeout:
            flag = False
        finally:
            sock.close()
            self.alive.value == False
        return flag
    
    def run(self, timeout=None, retry_time=3):
        while True:
            ret = self.serve(timeout)
            if ret:
                break
            print(f"Server timeouted, retrying in {retry_time} seconds...")
    
    def read(self):
        return self.is_alive() and self.alive.value, self.current_frame.copy()

if __name__ == "__main__":
    shape = (640, 640, 3)
    addr = os.getenv("HOST_ADDR", "127.0.0.1")
    port = os.getenv("HOST_VIDEO_P", 1234)

    video_capture = MultiProcessingSocketVideoCapture(shape, addr, port)
    video_capture.start()

    while video_capture.is_alive():
        ret, frame = video_capture.read()
        if ret:
            cv2.imshow("show", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            video_capture.terminate()
            quit()
