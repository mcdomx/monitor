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
import asyncio

import numpy as np
from PIL import Image

import cv2 as cv
from django.core.serializers.json import DjangoJSONEncoder
from confluent_kafka import Producer

# from traffic_monitor.services.service_abstract import ServiceAbstract
from traffic_monitor.services.ASYNC_config_synchronization import MessageConsumer
from traffic_monitor.services.elapsed_time import ElapsedTime
from traffic_monitor.websocket_channels import VideoChannel
from traffic_monitor.websocket_channels_factory import ChannelFactory
from traffic_monitor.services.detectors.detector_abstract import DetectorAbstract
from traffic_monitor.services.detectors.detector_cvlib import DetectorCVlib

BUFFER_SIZE = 512

logger = logging.getLogger('videodetection_service')


class ObjectDetectionService(MessageConsumer, ABC, DetectorCVlib):
    """


    """

    def __init__(self,
                 monitor_config: dict,
                 output_data_topic: str,  # Kafka topic to produce data to
                 ):
        """ Requires existing monitor.  1:1 relationship with a monitor but this is not
        enforced when creating the Monitor Service. """
        MessageConsumer.__init__(self, topic=monitor_config.get('monitor_name'), monitor_config=monitor_config)
        DetectorCVlib.__init__(self,
                               detector_model=monitor_config.get('detector_model'),
                               detector_confidence=monitor_config.get('detector_confidence'),
                               class_colors=monitor_config.get('class_colors'))

        self.monitor_name: str = monitor_config.get('monitor_name')
        self.name = f"ObjectDetectionService-{self.monitor_name}"
        self.channel_url = f"/ws/traffic_monitor/video/{monitor_config.get('monitor_name')}/"  # websocket channel address
        self.producer = Producer({'bootstrap.servers': '127.0.0.1:9092',
                                  'group.id': 'monitorgroup'})
        self.raw_queue: queue.Queue = queue.Queue(maxsize=50)
        self.detector_ready = False

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
        handle detector configuration changes
        :param msg:
        :return:
        """
        def _get_kwargs_value(kwargs, k: str):
            for kv in kwargs:
                if kv.get('field') == k:
                    return kv.get('value')

        key = msg.key().decode('utf-8')
        if key == 'config_change':
            decoded_msg = json.JSONDecoder().decode(msg.value().decode('utf-8'))
            f = decoded_msg.get('function')
            # not all 'config_change' messages call 'set_value' - 'keep_alive' is possible
            # we don't reset the detector for keep_alive messages
            if f is not 'set_value':
                return

            update_kwargs = decoded_msg.get('kwargs')
            if not update_kwargs:
                return

            # If the detector changed, update the detector values directly
            fields = [d.get('field') for d in update_kwargs]
            if 'detector_confidence' in fields:
                self.set_detector_confidence(_get_kwargs_value(update_kwargs, 'detector_confidence'))
            if 'detector_model' in fields:
                self.set_detector_model(_get_kwargs_value(update_kwargs, 'detector_model'))

    async def refresh_stream(self) -> cv.VideoCapture:
        """ Will get a new URL for the stream and returns a new VideoCapture object with the new url """
        response = requests.get('http://127.0.0.1:8000/get_monitor?monitor_name=MyMonitor&field=feed_url')
        if response.status_code != 200:
            raise Exception(f"Can't get URL.  Response Code: {response.status_code}")
        feed_url = json.loads(response.text)['feed_url']
        self.monitor_config['feed_url'] = feed_url
        cap = cv.VideoCapture(feed_url)

        # wait till cap is opened until continuing
        i = 1
        while not cap.isOpened():
            time.sleep(1)
            i += 1
            if i > 10:
                logger.error(f"\tTired of waiting to open video capture. Bailing.")
                raise Exception("Failed to open video feed.")

        return cap

    async def read_frames(self):
        """ Async process to read frames from a video stream. Places a frame on queue when detector is ready """
        cap = cv.VideoCapture(self.monitor_config.get('feed_url'))
        while self.running:
            try:
                if self.detector_ready:
                    try:
                        success, frame = cap.read()
                    except Exception as e:
                        raise Exception("read raised exception")
                    if success:
                        try:
                            self.raw_queue.put(frame)
                        except queue.Full:
                            _ = self.raw_queue.get()
                            self.raw_queue.put(frame)
                    else:
                        raise Exception("failed read")
                else:
                    cap.grab()

            except Exception as e:
                logger.error(f"read_frames failed: {e}")
                logger.error(f"CV VideoCapture Failed to read image. Resetting stream.")
                try:
                    cap = self.refresh_stream()
                except Exception as e:
                    logger.error(f"Stream Reset Failed. {e}")
                    self.running = False
                    break

    def _publish(self, frame, detections):
        """ Publishes detected frame and detection data """

        # send web-client updates using the Channels-Redis websocket
        channel: VideoChannel = ChannelFactory().get(self.channel_url)
        if channel:
            # this sends message to any front end that has created a WebSocket
            # with the respective channel_url address
            msg = {'image': frame, 'shape': frame.shape}
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

    async def detect_frames(self):
        """ Gets an available frame and launches the detection process  """
        self.detector_ready = True
        unhandled_error_count = 0
        while self.running:
            try:
                raw_frame = self.raw_queue.get(block=False)
                self.detector_ready = False
                det_frame, detections = await self.detect(raw_frame)
                self._publish(det_frame, detections)
                self.detector_ready = True
                unhandled_error_count = 0
            except queue.Empty:
                self.detector_ready = True
                await asyncio.sleep(.1)
                continue
            except Exception as e:
                logger.error(f"Unhandled Exception in detect_frames: {e}")
                unhandled_error_count += 1
                if unhandled_error_count > 10:
                    self.running = False

    async def polling(self):
        """ Async process that polls each second """
        while self.running:
            # poll to check for config changes
            msg = self.poll_kafka(0)

            # if the detector setting changed, we need to update the detector
            if msg is not None:
                self.handle_message(msg)

            await asyncio.sleep(1)

    async def start(self):
        """ Launch the async processes for object detection """
        if self.running:
            message = {'message': f"[{self.__class__.__name__}]: already running for'{self.monitor_name}'"}
            return message
        try:
            self.running = True
            await asyncio.gather(self.read_frames(), self.detect_frames(), self.polling())
            logger.info(f"[{self.monitor_name}] Stopped video detection service.")
        except Exception as e:
            message = {'message': f"[{self.__class__.__name__}]: Exception in detection service: {e}"}
            return message

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
