import cv2
import numpy as np

class ObtructionYOLODetector:
    def __init__(self, model_path, conf_thres=0.7, nms_thres=0.5):
        self.class_names = ["obtruction"]
        self.conf_threshold = conf_thres
        self.nms_threshold = nms_thres

        self.input_shape = (640, 640)
        self.__load_net(model_path)
        self.output_names = self.net.getUnconnectedOutLayersNames()


    def __load_net(self, model_path, use_myriad=False):
        self.net = cv2.dnn.readNet(model_path)

        # specify the target device as the Myriad processor on the NCS
        if use_myriad:
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_MYRIAD)
        else:
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)


    def detect(self, img):
        blob = cv2.dnn.blobFromImage(img, 1/255.0, self.input_shape)
        blob = cv2.dnn.blobFromImage(img, 1/255.0, (640, 640))
        self.net.setInput(blob)
        outputs = self.net.forward(self.output_names)
        return self.__process_ouputs(outputs)

    
    def __process_ouputs(self, outputs):
        # predictions.shape (1, 25200, 6)
        predictions = np.squeeze(outputs[0])
        predictions = predictions[predictions[:, 4] > self.conf_threshold]
        if predictions.shape[0] == 0: return [], [], []
        
        # convert (cx, cy, w, h) => (x, y, w, h)
        boxes = predictions[:, :4]
        boxes[:, 0] -= boxes[:, 2]/2
        boxes[:, 1] -= boxes[:, 3]/2
        boxes[:, 2] += boxes[:, 0]
        boxes[:, 3] += boxes[:, 1]

        # multiply box_confidence with class_confidence
        scores = np.max(predictions[:, 5:])
        scores *= np.expand_dims(predictions[:, 4], 1)
        scores = scores.squeeze(1)
        class_ids = np.argmax(predictions[:, 5:], axis=1)

        # apply nms
        index = cv2.dnn.NMSBoxes(boxes, scores, self.conf_threshold, self.nms_threshold)
        return list(class_ids[index]), list(boxes[index].astype(np.int32)), list(scores[index])

def draw_result(img, class_ids, boxes, scores, labels):
    for class_id, box, score in zip(class_ids, boxes, scores):
        cv2.rectangle(img, (box[0], box[1]), (box[2], box[3]), (255, 0, 0), 3)
        label = "%s: %.1f" % (labels[class_id], score)
        img = cv2.putText(img, label, (box[0]+3, box[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 100, 100), 4)

def detect_and_drawbboes(img, detector):

    for class_id, box, score in zip(*detector.detect(img)):
        cv2.rectangle(img, (box[0], box[1]), (box[2], box[3]), (255, 0, 0), 3)
        cv2.putText(img, )

    try:
        ratio = (box[2]-box[0]) / img.shape[1]
        theta = ratio * FRAME_WIDTH
        angle = FRAME_ANGLE-FRAME_WIDTH/2 + theta

        img = cv2.putText(img, f"Ratio: {ratio}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 100, 100), 4)
        img = cv2.putText(img, f"Theta: {theta/np.pi*180}", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 100), 4)
        img = cv2.putText(img, f"Theta: {angle/np.pi*180}", (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 100), 4)
    except UnboundLocalError as e:
        print("not obj found")

    return img