import logging
import numpy as np

import cvlib as cv
from cvlib.object_detection import populate_class_labels, draw_bbox

from traffic_monitor.detectors.detector import Detector


class DetectorCVlib(Detector):
    """
    Supports:
        yolov3-tiny
        yolov3

    Requires that .cfg file and .weights files are in ~/.cvlib/object_detection/yolo/yolov3
    """

    def __init__(self, name='cvlib detector', model='yolov3', verbosity: int = 0):
        Detector.__init__(self, name=name, model=model, verbosity=verbosity)

    def detect(self, frame: np.array, det_objs: set = None) -> (int, np.array, list):
        bbox, labels, conf = cv.detect_common_objects(frame, confidence=.5, model=self.model, )

        self.logger.info(labels)

        # only keep in the det_objs set
        if det_objs is not None:
            idxs = [i for i, l in enumerate(labels) if l in det_objs]
            labels = list(np.array(labels)[idxs])
            bbox = list(np.array(bbox)[idxs])
            conf = list(np.array(conf)[idxs])

        frame = draw_bbox(img=frame, bbox=bbox, labels=labels, confidence=conf, write_conf=False, )

        return 0, frame, labels

    def get_trained_objects(self) -> set:
        return set(populate_class_labels())
