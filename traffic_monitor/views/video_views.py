import logging
import time

import pafy
import cv2
import os
import cvlib as cv
from cvlib.object_detection import draw_bbox, populate_class_labels
import numpy as np

from django.http import StreamingHttpResponse

# from traffic_monitor.detectors.detector_cvlib import DetectorCVlib
from traffic_monitor.detectors.detector_factory import DetectorFactory


from traffic_monitor.models.model_class import Class

logger = logging.getLogger('view')


# VIDEO STREAM FUNCTIONS
def get_stream_url(cam: str) -> str:
    """
    Determine the true url of the video stream.
    Use YouTube url if not a local webcam.
    """

    if type(cam) is str and cam.isdigit():
        cam = int(cam)

    # test video feed
    read_pass = _test_cam(cam)

    # if capture fails, try as YouTube Stream
    # https://pypi.org/project/pafy/
    if not read_pass:
        if '/' in cam and 'youtube' in cam:  # a full video path was given
            cam = cam.split('/')[-1]
        try:
            video_pafy = pafy.new(cam)
        except Exception:
            raise Exception("No video stream found: {}".format(cam))
        # get most reasonable stream h x w < 350k
        res_limit = 105000
        stream_num = 0

        # use pafy to get the url of the stream
        # find stream with resolution within res_limit
        logger.debug("Available stream sizes:")
        for s in video_pafy.streams:
            logger.debug(f"\t{s}")

        for i, stream in enumerate(video_pafy.streams):
            x, y = np.array(stream.resolution.split('x'), dtype=int)
            if x * y < res_limit:
                stream_num = i
            else:
                break

        stream = video_pafy.streams[stream_num]
        logger.debug(f"Selected stream: {video_pafy.streams[stream_num]}")

        # test stream
        read_pass = _test_cam(stream.url)

        if read_pass:
            cam = stream.url
            logger.info("YouTube Video Stream Detected!")
            logger.info("Video Resolution : {}".format(stream.resolution))

    logger.info("Video Test       : {}".format("OK" if read_pass else "FAIL - check that streamer is publishing"))

    if not read_pass:
        raise Exception("Can't acquire video source: {}".format(cam))

    return cam


def _test_cam(cam: str) -> bool:
    cap = cv2.VideoCapture(cam)
    read_pass = cap.grab()
    cap.release()

    if not read_pass:
        return False

    return True


def get_camfps(cam: str) -> float:
    """
    Return the camera's published FPS.
    """
    cap = cv2.VideoCapture(cam)
    cam_fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()

    return cam_fps


# https://github.com/arunponnusamy/object-detection-opencv/raw/master/yolov3.cfg
# https://pjreddie.com/media/files/yolov3.weights

def gen_stream(detector_id):
    """Video streaming generator function."""

    # set source of video stream
    cam_stream = '1EiC9bvVGnk'
    cam_name = get_stream_url(cam_stream)
    cap = cv2.VideoCapture(cam_name)

    # set the detector to use (supports: yolov3, yolov3-tiny)
    rv = DetectorFactory().get(detector_id)
    if not rv['success']:
        return rv['message']

    detector = rv.get('detector').get('detector')
    logger.info(f"Using detector: {detector.name}  model: {detector.model}")

    interval = 100
    count = 0
    while True:

        time.sleep(.02)

        success, frame = cap.read()

        if not success:
            continue

        count += 1
        if count % interval == 0:
            _, frame, detections = detector.detect(frame)
            count = 0

        frame = cv2.imencode('.jpg', frame)[1].tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


def video_feed(request, detector_id):
    """Video streaming route. Put this in the src attribute of an img tag."""

    return StreamingHttpResponse(gen_stream(detector_id), content_type="multipart/x-mixed-replace;boundary=frame")


def get_class_data(detector_id):
    """ Get class data including class_name, class_id, is_mon_on and is_log_on"""
    d = DetectorFactory().get(detector_id).get('detector').get('detector')
    class_data = d.get_class_data(detector_id)

    return class_data


def toggle_box(action: str, class_id: str, detector_id: str):
    d = DetectorFactory().get(detector_id).get('detector').get('detector')
    if action == 'mon':
        rv = d.toggle_monitor(class_id)
    elif action == 'log':
        rv = d.toggle_log(class_id)
    else:
        return {'success': False, 'message': f"ERROR: can only toggle 'mon' or 'log', not '{action}'"}

    return rv


def toggle_all(detector_id: str, action: str):
    d = DetectorFactory().get(detector_id).get('detector').get('detector')
    if action == 'mon':
        rv = d.toggle_all_mon()
    elif action == 'log':
        rv = d.toggle_all_log()
    else:
        return {'success': False, 'message': f"ERROR: can only toggle mon or log, not {action}"}

    return rv



# END VIDEO STEAMING FUNCTIONS ##########################
