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

import numpy as np
from PIL import Image

import cv2 as cv
from django.core.serializers.json import DjangoJSONEncoder
from confluent_kafka import Producer

from traffic_monitor.services.detectors.detector_cvlib import DetectorCVlib
from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.websocket_channels import VideoChannel
from traffic_monitor.websocket_channels_factory import ChannelFactory


BUFFER_SIZE = 512

logger = logging.getLogger('videodetection_service')


class VideoDetectionService(ServiceAbstract, DetectorCVlib, ABC):
    """


    """

    def __init__(self,
                 monitor_config: dict,
                 output_data_topic: str,  # Kafka topic to produce data to
                 ):
        """ Requires existing monitor.  1:1 relationship with a monitor but this is not
        enforced when creating the Monitor Service. """
        ServiceAbstract.__init__(self, monitor_config=monitor_config, output_data_topic=output_data_topic)
        DetectorCVlib.__init__(self, monitor_config=monitor_config)
        self.monitor_name: str = monitor_config.get('monitor_name')
        self.name = f"VideoDetectionService-{self.monitor_name}"
        self.channel_url = f"/ws/traffic_monitor/video/{monitor_config.get('monitor_name')}/"  # websocket channel address
        self.producer = Producer({'bootstrap.servers': '127.0.0.1:9092',
                                  'group.id': 'monitorgroup'})
        self.raw_queue: queue.Queue = queue.Queue(maxsize=50)
        self.detector_ready = True

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
        update the detector since it is not an AbstractService listening for config changes.
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
            # the detector will determine what needs to be changes
            self.set_detector(update_kwargs)

    def _run_detect_thread(self, frame):
        self.detector_ready = False
        frame, labels = self.detect(frame)
        self._publish(frame, labels)
        time.sleep(self.monitor_config.get('detector_sleep_throttle'))
        self.detector_ready = True

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

        while self.running:

            # poll to check for config changes
            msg = self.poll_kafka(0)

            # handle other messages we may need to address
            if msg is not None:
                self.handle_message(msg)

            try:
                _ = cap.grab()
                success, frame = cap.read()

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

                # if detector is ready, perform frame detection
                if self.detector_ready:
                    try:
                        # The thread will handle the outgoing communication of the result
                        self.detector_ready = False
                        threading.Thread(target=self._run_detect_thread, args=(frame,), daemon=True).start()
                    except Exception as e:
                        logger.error(f"{self.__class__.__name__}: Running detect thread failed: {e}")

            except Exception as e:
                logger.error(f"{self.__class__.__name__}: Could not pull image: {e}")
                continue

        # make sure that running is false in case something else stopped this loop
        self.running = False
        logger.info(f"[{self.monitor_name}] Stopped video detection service.")

    def _reset_stream(self) -> cv.VideoCapture:
        logger.error(f"CV Video Capture Failed to read image. Resetting stream.")
        response = requests.get(
            'http://127.0.0.1:8000/get_monitor?monitor_name=MyMonitor&field=feed_url')
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
