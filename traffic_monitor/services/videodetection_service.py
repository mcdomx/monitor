"""
A streaming service has the task of placing data from the stream
on a queue.

This is a service that will take images from a video stream
and run image detection on them.

The resulting images will be placed on a queue.

The detection service will return detections of all objects that it has been trained
to detect.  The detected image will also highlight all trained objects that are detected.

Any services that use the data will have the task of only processing data that the
service has been configured to process.

"""

import queue
import logging
from abc import ABC
import base64
import io
import json
import time
import requests
import threading
import os

import numpy as np
from PIL import Image

import cv2 as cv
from django.core.serializers.json import DjangoJSONEncoder
from confluent_kafka import Producer

from traffic_monitor.services.detectors.detector_factory import DetectorFactory
from traffic_monitor.services.detectors.detector_abstract import DetectorAbstract
from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.websocket_channels import VideoChannel
from traffic_monitor.websocket_channels_factory import ChannelFactory

BUFFER_SIZE = 512
KAFKA_HOST = os.getenv('KAFKA_HOST', '0.0.0.0')
KAFKA_PORT = os.getenv('KAFKA_PORT', 9092)
KAFKA_GROUPID = os.getenv('KAFKA_GROUPID', 'monitorgroup')
APP_HOST = os.getenv('APP_HOST', '0.0.0.0')
APP_PORT = os.getenv('APP_PORT', 8000)

logger = logging.getLogger('videodetection_service')


class VideoDetectionService(ServiceAbstract, ABC):
    """
    VideoDetectionService will compose a detector based on the values of monitor_config.  This allows
    This class to work with a variety of different detection models or even change then run-time.

    This class will pull images from a stream identified in monitor_config and send them to the detector
    for detection.  The results of the detection are handled by this class; the image is sent over a
    websocket to any subscribing front-end socket and the detections are communicated to the backend
    over Kafka where they may be read by other interested threads (namely logging and notification).

    Using inheritance for the detector proved more efficient, but limited the usefulness and reusability of
    this class so composition is used instead.

    """
    def __init__(self,
                 monitor_config: dict,
                 output_data_topic: str,  # Kafka topic to produce data to
                 ):
        """ Requires existing monitor.  1:1 relationship with a monitor but this is not
        enforced when creating the Monitor Service. """
        global KAFKA_HOST, KAFKA_PORT, KAFKA_GROUPID

        ServiceAbstract.__init__(self, monitor_config=monitor_config, output_data_topic=output_data_topic)
        self.monitor_name: str = monitor_config.get('monitor_name')
        self.name = f"VideoDetectionService-{self.monitor_name}"
        self.channel_url = f"/ws/traffic_monitor/video/{monitor_config.get('monitor_name')}/"  # websocket channel address
        self.producer = Producer({'bootstrap.servers': f'{KAFKA_HOST}:{KAFKA_PORT}',
                                  'group.id': KAFKA_GROUPID})
        self.raw_queue: queue.Queue = queue.Queue(maxsize=50)
        self.detector_ready = False
        self.detector: DetectorAbstract = DetectorFactory().get_detector(monitor_config=self.monitor_config)

    def __str__(self):
        rv = self.__dict__
        str_rv = {k: f"{v}" for k, v in rv.items()}

        return f"{str_rv}"

    def delivery_report(self, err, msg):
        """ Kafka support function.  Called once for each message produced to indicate delivery result.
            Triggered by poll() or flush(). """
        if err is not None:
            logger.error(f'{self.__class__.__name__}: Message delivery failed: {err}')
        else:
            logger.debug(f'{self.__class__.__name__}: Message delivered to {msg.topic()} partition:[{msg.partition()}]')

    def handle_message(self, msg):
        """
        The abstract service will make the config changes, here we
        update the detector since it is not listening for config changes on its own.
        :param msg:
        :return:
        """
        key = msg.key().decode('utf-8')
        if key == 'config_change':
            decoded_msg = json.JSONDecoder().decode(msg.value().decode('utf-8'))
            logger.info(f"{self.__class__.__name__}: Handling ({key}): {decoded_msg}")
            f = decoded_msg.get('function')
            # not all 'config_change' messages will necessarily call 'set_value'
            if f != 'set_value':
                return

            update_kwargs = decoded_msg.get('kwargs')
            if not update_kwargs:
                return

            # update the detector directly - it does not listen for changes
            # the detector will determine what needs to be changed
            self.detector.set_detector_value(update_kwargs)

    def _run_detect_thread(self, frame):
        self.detector_ready = False
        try:
            frame, labels = self.detector.detect(frame)
            self._publish(frame, labels)
            time.sleep(self.monitor_config.get('detector_sleep_throttle'))
            self.detector_ready = True
        except:
            self.detector_ready = True
            logger.error(f"{self.__class__.__name__}: _run_detect_failed")

    def run(self):
        """
        This will start the service by calling threading.Thread.start()
        Frames will be placed in respective queues.
        """
        try:
            # set source of video stream
            cap = cv.VideoCapture(self.monitor_config.get('feed_url'))

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Failed to create a video stream.")
            logger.error(e)
            return

        self.detector_ready = True
        while self.running:

            # poll to check for config changes
            msg = self.poll_kafka(0)

            # handle other messages we may need to address
            if msg is not None:
                self.handle_message(msg)

            try:
                if self.detector_ready:
                    success, frame = cap.read()
                    try:
                        # The thread will handle the outgoing communication of the result
                        threading.Thread(target=self._run_detect_thread, args=(frame,), daemon=True).start()
                    except Exception as e:
                        logger.error(f"{self.__class__.__name__}: Running detect thread failed: {e}")
                else:
                    success = cap.grab()

                i = 0
                while not success:
                    success, frame = cap.read()
                    i += 1
                    if i >= 10:
                        logger.info(f"Tried {i} times to get an image and failed.")
                        cap = self._reset_stream()
                        if cap is None:
                            message = "Failed to reset stream with new URL."
                            logger.error(message)
                            self.running = False
                            raise Exception(message)
                        else:
                            logger.error("Successfully reset stream with new URL.")

            except Exception as e:
                logger.error(f"{self.__class__.__name__}: Could not pull image: {e}")
                continue

        # make sure that running is false in case something else stopped this loop
        self.running = False
        logger.info(f"[{self.monitor_name}] Stopped video detection service.")

    def _reset_stream(self) -> cv.VideoCapture:
        logger.error(f"CV Video Capture Failed to read image. Resetting stream.")
        response = requests.get(
            f'http://{APP_HOST}:{APP_PORT}/get_monitor?monitor_name=MyMonitor&field=feed_url')
        if response.status_code == 200:
            feed_url = json.loads(response.text)['feed_url']
            self.monitor_config['feed_url'] = feed_url
            cap = cv.VideoCapture(feed_url)

            # wait till stream is opened until continuing
            i = 1
            while not cap.isOpened():
                time.sleep(1)
                logger.error(f"\twaiting to open stream...{i}\r")
                i += 1
                if i > 10:
                    logger.error(f"\tTired of waiting to open video capture. Bailing.")
                    break

            return cap

        else:
            logger.error(
                f"Couldn't get a refreshed URL stream.  Response Code: {response.status_code}. Bailing.")
            self.running = False  # this will stop thread and the monitor_service will restart it

    def _publish(self, frame, detections):
        """ Publishes detected frame and detection data """

        # send web-client updates using the Channels-Redis websocket
        channel: VideoChannel = ChannelFactory().get(self.channel_url)
        if channel:
            # this sends message to any front end that has created a WebSocket
            # with the respective channel_url address
            img = self._convert_imgarray_to_inmem_base64_jpg(frame)  # convert to in-memory file
            msg = {'image': img, 'shape': frame.shape}
            channel.send(text_data=DjangoJSONEncoder().encode(msg))

        # publish the detection data to kafka topic
        try:
            self.producer.poll(0)
            self.producer.produce(topic=self.monitor_name,
                                  key='detector_detection',
                                  value=json.JSONEncoder().encode(detections),
                                  callback=self.delivery_report,
                                  )
            self.producer.flush()
        except Exception as e:
            logger.error(f"[{self.name}] Unhandled Exception publishing detection data: {e.args}")

    @staticmethod
    def _convert_imgarray_to_inmem_base64_jpg(img_array: np.array) -> base64:
        """
        ref: https://stackoverflow.com/questions/42503995/how-to-get-a-pil-image-as-a-base64-encoded-string
        Convert an image array into an in-memory base64 RGB image.
        The return value can be placed in an HTML src tag:
        <img src="data:image/jpg;base64,<<base64 encoding>>" height="" width="" alt="image">
        :param img_array: a numpy image
        :return: base64 image in ascii characters. The returned object can be placed in an <img> html tag's src (src="data:image/jpg;base64,<<return value>>")
        """
        # convert image from BGR to RGB
        img_array = img_array[:, :, ::-1]

        # create an in-memory rgb image from array using PIL library
        rgbimg = Image.fromarray(img_array, mode='RGB')

        b = io.BytesIO()  # create an empty byte object
        rgbimg.save(b, format='JPEG')  # save the rgb in-memory file to the object
        b.seek(0)  # move pointer back to the start of memory space
        img_bytes = b.read()  # read memory space into a new variable

        base64_img = base64.b64encode(img_bytes)  # encode the image to base64
        base64_ascii_img = base64_img.decode('ascii')  # finally, decode it to ascii characters

        return base64_ascii_img
