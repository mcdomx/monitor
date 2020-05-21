import logging
import numpy as np

import cvlib as cv
from cvlib.object_detection import populate_class_labels, draw_bbox

from traffic_monitor.detectors.detector import Detector_Abstract

from traffic_monitor.models.model_class import Class
from traffic_monitor.models.model_detector import Detector


class DetectorCVlib(Detector_Abstract):
    """
    Supports:
        yolov3-tiny
        yolov3

    Requires that .cfg file and .weights files are in ~/.cvlib/object_detection/yolo/yolov3
    """

    def __init__(self, name=None, model=None):
        if name is None:
            name = 'detector_cvlib'
        if model is None:
            model = 'yolov3-tiny'
        if model not in ['yolov3-tiny', 'yolov3']:
            model = 'yolov3-tiny'

        Detector_Abstract.__init__(self, name=name, model=model)

        # save new detector in db
        obj, created = Detector.objects.update_or_create(id=f"{name}__{model}", name=name, model=model)
        obj.save()

        self.load_classes()
        self.monitored_objects = None
        self.logged_objects = None
        self.update_monitored_objects()
        self.update_logged_objects()

    def update_monitored_objects(self):
        self.monitored_objects = Class.get_monitored_objects(self.id)

    def update_logged_objects(self):
        self.logged_objects = Class.get_logged_objects(self.id)

    def detect(self, frame: np.array) -> (int, np.array, list):
        bbox, labels, conf = cv.detect_common_objects(frame, confidence=.5, model=self.model)

        # only log detections that are being logged
        log_idxs = [i for i, l in enumerate(labels) if l in self.logged_objects]
        self.logger.info(list(np.array(labels)[log_idxs]))
        print(list(np.array(labels)[log_idxs]))

        # only keep detections that are being monitored
        mon_idxs = [i for i, l in enumerate(labels) if l in self.monitored_objects]
        labels = list(np.array(labels)[mon_idxs])
        bbox = list(np.array(bbox)[mon_idxs])
        conf = list(np.array(conf)[mon_idxs])

        frame = draw_bbox(img=frame, bbox=bbox, labels=labels, confidence=conf, write_conf=False, )

        return 0, frame, labels

    def get_trained_objects(self) -> set:
        return set(populate_class_labels())

    def toggle_monitor(self, class_id):
        rv = Class.toggle_mon(class_id=class_id, detector_id=self.id)
        self.update_monitored_objects()
        return rv

    def toggle_log(self, class_id):
        rv = Class.toggle_log(class_id=class_id, detector_id=self.id)
        self.update_logged_objects()
        return rv

    def toggle_all_mon(self):
        rv = Class.toggle_all_mon(self.id)
        self.update_monitored_objects()
        return rv

    def toggle_all_log(self):
        rv = Class.toggle_all_log(self.id)
        self.update_logged_objects()
        return rv

    @staticmethod
    def get_class_data(detector_id: str):
        return Class.objects.filter(detector_id=detector_id).values()

    def load_classes(self):
        rs = Class.objects.filter(detector=self.id)
        classes = self.get_trained_objects()

        if len(rs) - len(classes) != 0:
            # some items maybe already loaded
            # preserve existing class settings and load missing ones
            loaded_classes = [r.class_name for r in rs]
            missing_classes = set(classes) - set(loaded_classes)

            load_list = []
            for class_name in missing_classes:
                class_id = class_name.replace(" ", "_")
                load_list.append(Class.objects.create(
                    key=f"{self.id}__{class_id}",
                    class_name=class_name,
                    class_id=class_id,
                    detector=Detector.objects.get(pk=self.id),
                    monitor=True,
                    log=True
                ))
