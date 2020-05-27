import logging
import numpy as np
import queue

import cvlib as cv
from cvlib.object_detection import populate_class_labels, draw_bbox

from traffic_monitor.detectors.detector_abstract import Detector_Abstract

from traffic_monitor.models.model_class import Class
from traffic_monitor.models.model_detector import Detector


class DetectorCVlib(Detector_Abstract):
    """
    Supports:
        yolov3-tiny
        yolov3

    Requires that .cfg file and .weights files are in ~/.cvlib/object_detection/yolo/yolov3
    """

    def __init__(self, detector_id: str, queue_detready: queue.Queue, queue_detframe: queue.Queue):
        Detector_Abstract.__init__(self, detector_id, queue_detready, queue_detframe)
        self.load_classes()
        self.update_monitored_objects()
        self.update_logged_objects()

    def detect(self, frame: np.array) -> (int, np.array, list, list):
        bbox, labels, conf = cv.detect_common_objects(frame, confidence=.5, model=self.model)

        # only log detections that are being logged
        log_idxs = [i for i, l in enumerate(labels) if l in self.logged_objects]
        log_labels = list(np.array(labels)[log_idxs])

        # only keep detections that are being monitored
        mon_idxs = [i for i, l in enumerate(labels) if l in self.monitored_objects]
        mon_labels = list(np.array(labels)[mon_idxs])
        bbox = list(np.array(bbox)[mon_idxs])
        conf = list(np.array(conf)[mon_idxs])

        frame = draw_bbox(img=frame, bbox=bbox, labels=mon_labels, confidence=conf, write_conf=False, )

        return 0, frame, log_labels, mon_labels

    def get_trained_objects(self) -> set:
        return set(populate_class_labels())
