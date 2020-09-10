import queue
import traceback
import logging
import numpy as np

from cvlib.object_detection import populate_class_labels, draw_bbox, detect_common_objects

from traffic_monitor.detector_machines.detector_machine_abstract import DetectorMachineAbstract

logger = logging.getLogger('detector')


class DetectorMachineCVlib(DetectorMachineAbstract):
    """
    Implementation of DetectorAbstract.  This implementation is from the OpenCV
    implementation of object instance detection.

    Supports:
        yolov3-tiny
        yolov3

    Requires that .cfg file and .weights files are in ~/.cvlib/object_detection/yolo/yolov3
    """

    def __init__(self,
                 monitor_config: dict,
                 input_image_queue: queue.Queue,
                 output_image_queue: queue.Queue,
                 output_data_topic: str):
        DetectorMachineAbstract.__init__(self,
                                         monitor_config=monitor_config,
                                         input_image_queue=input_image_queue,
                                         output_image_queue=output_image_queue,
                                         output_data_topic=output_data_topic)
        self.observers = []
        self.subject_name = 'detector_cvlib'

    def detect(self, frame: np.array) -> (np.array, list):
        try:
            bbox, labels, conf = detect_common_objects(frame, confidence=.25, model=self.detector_model)
            frame = draw_bbox(img=frame, bbox=bbox, labels=labels, confidence=conf, write_conf=False)
            return frame, labels
        except Exception as e:
            logger.info(f"cvlib Exception: {e}")
            # this detector has a problem when an error is thrown
            # as a result, we will stop the thread and let the
            # videodetection_service create a new thread
            self.running = False
            # logger.info(traceback.print_stack())

    @classmethod
    def get_trained_objects(cls) -> list:
        return list(populate_class_labels())
