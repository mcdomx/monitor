import numpy as np

from cvlib.object_detection import populate_class_labels, draw_bbox, detect_common_objects

from traffic_monitor.detector_machines.detector_machine_abstract import DetectorMachineAbstract


class DetectorMachineCVlib(DetectorMachineAbstract):
    """
    Implementation of DetectorAbstract.  This implementation is from the OpenCV
    implementation of object instance detection.

    Supports:
        yolov3-tiny
        yolov3

    Requires that .cfg file and .weights files are in ~/.cvlib/object_detection/yolo/yolov3
    """

    def __init__(self, **kwargs):
        DetectorMachineAbstract.__init__(self, **kwargs)
        self.observers = []
        self.subject_name = 'detector_cvlib'

    def detect(self, frame: np.array) -> (int, np.array, list):
        bbox, labels, conf = detect_common_objects(frame, confidence=.5, model=self.model)

        # # only log detections that are being logged
        # log_idxs = [i for i, l in enumerate(labels) if l in self.logged_objects]
        # log_labels = list(np.array(labels)[log_idxs])
        #
        # # only keep detections that are being monitored
        # mon_idxs = [i for i, l in enumerate(labels) if l in self.notified_objects]
        # mon_labels = list(np.array(labels)[mon_idxs])
        # bbox = list(np.array(bbox)[mon_idxs])
        # conf = list(np.array(conf)[mon_idxs])

        # frame = draw_bbox(img=frame, bbox=bbox, labels=mon_labels, confidence=conf, write_conf=False, )
        frame = draw_bbox(img=frame, bbox=bbox, labels=labels, confidence=conf, write_conf=False, )

        # return 0, frame, log_labels, mon_labels
        return 0, frame, labels

    @classmethod
    def get_trained_objects(cls) -> list:
        return list(populate_class_labels())
