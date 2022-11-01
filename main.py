from logging import exception
import time
import numpy as np
import cv2
import os

from videocapture import MultiProcessingSocketVideoCapture
from rasp_controller import MultiProcessingSocketLidarController
from detect import ObtructionYOLODetector, draw_result

ADDR = "0.0.0.0"
VIDEO_PORT = os.getenv("HOST_VIDEO_P")
LIDAR_PORT = os.getenv("HOST_LIDAR_P")

FRAME_WIDTH = np.deg2rad(120)

mouse_controlling_flag = False
speed = 126
distance = float("inf")

def handle(event, x, y, flags, param):
    global mouse_controlling_flag
    global speed
    if event == cv2.EVENT_LBUTTONDOWN:
        mouse_controlling_flag = not mouse_controlling_flag
    if event == cv2.EVENT_MOUSEMOVE and mouse_controlling_flag:
        absolute_v = min(abs(y-320)/2, 126)
        speed = 126+absolute_v if y>320 else 126-absolute_v+1
        
        

if __name__ == "__main__":
    video_capture = MultiProcessingSocketVideoCapture((640, 640, 3), ADDR, VIDEO_PORT)
    lidar = MultiProcessingSocketLidarController(ADDR, LIDAR_PORT)

    video_capture.start()
    lidar.start()

    detector = ObtructionYOLODetector("cones.onnx", conf_thres=0.3, nms_thres=0.8)

    while not lidar.connected():
        time.sleep(0.1)
    
    print("Object connected")
    cv2.imshow("show", np.random.random((640, 640))*512)
    cv2.setMouseCallback("show", handle)

    while video_capture.is_alive():
        ret, frame = video_capture.read()
        if ret:
            if not (isinstance(frame, np.ndarray) and frame.any()):
                continue

            try:
                class_ids, boxes, scores = detector.detect(frame)
            except Exception as e:
                print(e)
            
            try:
                lidar.set_motor_speed(speed)
            except Exception as e:
                print("Error occurred while setting motor speed", e)
                
            distance = float("inf")
            if len(boxes):
                i = np.argmax(scores)
                box = boxes[i]
                score = scores[i]

                print("Obbstraction detected! Starting lidar...")
                x = np.mean([box[0], box[2]])
                frame_angle = x/frame.shape[0] * FRAME_WIDTH
                abb_angle = frame_angle + (np.pi-FRAME_WIDTH)/2

                ## Controlling LIDAR
                timestamp, d = lidar.get_distance(np.rad2deg(abb_angle))
                distance = d

                if timestamp:
                    print("Lidar detected!,", timestamp, d)

                ## Update ui
                cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (255, 0, 0), 1)
                frame = cv2.putText(
                    frame, str(score), (box[0]+3, box[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 100, 100), 1)
                frame = cv2.putText(
                    frame, str(distance), (20, 20), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 100, 100), 1
                )
                
            if mouse_controlling_flag:
                frame = cv2.line(frame, (320, 65), (320, 575), (0, 200, 30), 3)
                frame = cv2.line(frame, (65, 320), (575, 320), (0, 200, 30), 2)
            cv2.imshow("show", frame)
    
        if cv2.waitKey(1) & 0xFF == ord("q"):
            video_capture.terminate()
            print("quiting")
            quit()

    print("video_capture dead")