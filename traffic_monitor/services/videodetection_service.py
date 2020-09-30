# """
# A streaming service has the task of placing data from the stream
# on a queue.
#
# This is a service that will take images from a video stream
# and run image detection on them.
#
# The resulting images will be placed on a queue.
#
# The detection service will return detections of all objects that it has been trained
# to detect.  The detected image will also highlight all trained objects that are detected.
#
# Any services that use the data will have the task of only processing data that the
# service has been configured to process.
#
# """
#
# import queue
# import logging
# from abc import ABC
# import base64
# import io
# import json
# import time
# import requests
#
# import numpy as np
# from PIL import Image
#
# import cv2 as cv
# from django.core.serializers.json import DjangoJSONEncoder
#
# from traffic_monitor.detector_machines.detector_machine_factory import DetectorMachineFactory
# from traffic_monitor.services.service_abstract import ServiceAbstract
# from traffic_monitor.services.elapsed_time import ElapsedTime
# from traffic_monitor.websocket_channels import VideoChannel
# from traffic_monitor.websocket_channels_factory import ChannelFactory
#
# BUFFER_SIZE = 512
#
# logger = logging.getLogger('videodetection_service')
#
#
# class VideoDetectionService(ServiceAbstract, ABC):
#     """
#
#
#     """
#
#     def __init__(self,
#                  monitor_config: dict,
#                  output_data_topic: str,  # Kafka topic to produce data to
#                  ):
#         """ Requires existing monitor.  1:1 relationship with a monitor but this is not
#         enforced when creating the Monitor Service. """
#         ServiceAbstract.__init__(self, monitor_config=monitor_config, output_data_topic=output_data_topic)
#         self.monitor_name: str = monitor_config.get('monitor_name')
#         self.name = f"VideoDetectionService-{self.monitor_name}"
#         self.input_image_queue: queue.Queue = queue.Queue(BUFFER_SIZE)
#         self.output_image_queue: queue.Queue = queue.Queue(BUFFER_SIZE)
#         self.channel_url = f"/ws/traffic_monitor/video/{monitor_config.get('monitor_name')}/"  # websocket channel address
#
#         # DETECTOR STATES
#         self.show_full_stream = False
#
#         self.detector = None
#         self._set_detector()
#
#     def __str__(self):
#         rv = self.__dict__
#         str_rv = {k: f"{v}" for k, v in rv.items()}
#
#         return f"{str_rv}"
#
#     def _set_detector(self):
#         self.detector = DetectorMachineFactory().get_detector_machine(monitor_config=self.monitor_config,
#                                                                       input_image_queue=self.input_image_queue,
#                                                                       output_image_queue=self.output_image_queue,
#                                                                       output_data_topic=self.output_data_topic)
#
#     def get_next_frame(self):
#         q = self.output_image_queue.get()
#         return q.get()
#
#     def handle_message(self, msg):
#         """
#         The abstract service will make the config changes, here we
#         restart the detector if the detector changed
#         :param msg:
#         :return:
#         """
#         key = msg.key().decode('utf-8')
#         if key == 'config_change':
#             decoded_msg = json.JSONDecoder().decode(msg.value().decode('utf-8'))
#             f = decoded_msg.get('function')
#             # not all 'config_change' messages call 'set_value' - 'keep_alive' is possible
#             # we don't reset the detector for keep_alive messages
#             if f is not 'set_value':
#                 return
#
#             update_kwargs = decoded_msg.get('kwargs')
#             if not update_kwargs:
#                 return
#             fields = [d.get('field') for d in update_kwargs]
#             if 'detector_name' in fields or 'detector_model' in fields:
#                 # restart detector
#                 logger.info(f"Resetting detector with update configuration: {update_kwargs}")
#                 self.detector.stop()
#                 self.detector.join()
#                 self._set_detector()
#                 self.detector.start()
#
#     def _reset_detector(self):
#         logger.warning(
#             f"Restarting {self.monitor_config.get('detector_name')}:{self.monitor_config.get('detector_model')} for {self.monitor_name}")
#         self._set_detector()
#         self.detector.start()
#
#     def _reset_stream(self) -> cv.VideoCapture:
#         logger.error(f"CV Video Capture Failed to read image. Resetting stream.")
#         response = requests.get(
#             'http://127.0.0.1:8000/get_monitor?monitor_name=MyMonitor&field=feed_url')
#         if response.status_code == 200:
#             feed_url = json.loads(response.text)['feed_url']
#             self.monitor_config['feed_url'] = feed_url
#             cap = cv.VideoCapture(feed_url)
#
#             # wait till stream is opened until continuing
#             i = 1
#             while not cap.isOpened():
#                 time.sleep(1)
#                 logger.error(f"\twaiting to open stream...{i}\r")
#                 i += 1
#                 if i > 10:
#                     logger.error(f"\tTired of waiting to open video capture. Bailing.")
#                     break
#
#             return cap
#
#         else:
#             logger.error(
#                 f"Couldn't get a refreshed URL stream.  Response Code: {response.status_code}. Bailing.")
#             self.running = False  # this will stop thread and the monitor_service will restart it
#
#     def run(self):
#         """
#         This will start the service by calling threading.Thread.start()
#         Frames will be placed in respective queues.
#         """
#         try:
#             # set source of video stream
#             cap = cv.VideoCapture(self.monitor_config.get('feed_url'))
#
#             # start the detector machine
#             self.detector.start()
#
#         except Exception as e:
#             logger.error(f"[{self.__class__.__name__}] Failed to create a video stream.")
#             logger.error(e)
#             return
#
#         timer = ElapsedTime()
#         while self.running:
#
#             # poll to check for config changes
#             msg = self.poll_kafka(0)
#
#             # if the detector setting changed, we need to create and start a new detector
#             if msg is not None:
#                 self.handle_message(msg)
#
#             # first, let's see if there is an image ready to pull from the output queue
#             try:
#                 detected_image = self.output_image_queue.get_nowait()
#                 image_array: np.array = detected_image.get('frame')
#                 image = self._convert_imgarray_to_inmem_base64_jpg(image_array)  # convert to in-memory file
#
#                 # send web-client updates using the Channels-Redis websocket
#                 channel: VideoChannel = ChannelFactory().get(self.channel_url)
#                 if channel:
#                     # this sends message to any front end that has created a WebSocket
#                     # with the respective channel_url address
#                     msg = {'image': image, 'shape': image_array.shape}
#                     channel.send(text_data=DjangoJSONEncoder().encode(msg))
#
#             except queue.Empty:
#                 pass
#
#             try:
#                 _ = cap.grab()
#                 success, frame = cap.read()
#
#                 i = 0
#                 while not success:
#                     success, frame = cap.read()
#                     i += 1
#                     if i >= 10:
#                         logger.info(f"Tried {i} times to get an image and failed.")
#                         cap = self._reset_stream()
#                         if cap is None:
#                             logger.error("Failed to reset stream with new URL.")
#                         else:
#                             logger.error("Successfully reset stream with new URL.")
#
#                 if cap is None or not success:
#                     self.running = False
#                     raise Exception("Can't read an image from the URL feed.")
#
#                 # if the detector stopped for some reason, create a new thread
#                 if not self.detector.is_alive():
#                     self._reset_detector()
#
#                 # if detector is ready, perform frame detection
#                 if self.detector.is_ready:
#                     try:
#                         # the detector will perform detection on this
#                         # image and place the resulting image on the
#                         # output_image_queue and send detection data using Kafka
#                         self.input_image_queue.put(frame, block=False)
#
#                     except queue.Full:
#                         # if queue is full skip, drop an image to make room
#                         logger.error("Detector queue was full.  Removed an image to make room.")
#                         _ = self.input_image_queue.get()
#                         self.input_image_queue.put(frame, block=False)
#
#             except Exception as e:
#                 logger.error(f"{self.__class__.__name__}: Could not pull image: {e}")
#                 continue
#
#         # make sure that running is false in case something else stopped this loop
#         self.running = False
#
#         # stop the detector service
#         self.detector.stop()
#         self.detector.join()
#         self.consumer.close()
#         logger.info(f"[{self.monitor_name}] Stopped video detection service.")
#
#     @staticmethod
#     def get_trained_objects(detector_name) -> list:
#         return DetectorMachineFactory().get_trained_objects(detector_name)
#
#     @staticmethod
#     def _convert_imgarray_to_inmem_base64_jpg(img_array: np.array) -> base64:
#         """
#         ref: https://stackoverflow.com/questions/42503995/how-to-get-a-pil-image-as-a-base64-encoded-string
#         Convert an image array into an in-memory base64 RGB image.
#         The return value can be placed in an HTML src tag:
#         <img src="data:image/jpg;base64,<<base64 encoding>>" height="" width="" alt="image">
#         :param img_array: a numpy image
#         :return: base64 image in ascii characters. The returned object can be placed in an <img> html tag's src (src="data:image/jpg;base64,<<return value>>")
#         """
#         # convert image from BGR to RGB
#         img_array = img_array[:, :, ::-1]
#
#         # create an in-memory rgb image from array using PIL library
#         rgbimg = Image.fromarray(img_array, mode='RGB')
#
#         b = io.BytesIO()  # create an empty byte object
#         rgbimg.save(b, format='JPEG')  # save the rgb in-memory file to the object
#         b.seek(0)  # move pointer back to the start of memory space
#         img_bytes = b.read()  # read memory space into a new variable
#
#         base64_img = base64.b64encode(img_bytes)  # encode the image to base64
#         base64_ascii_img = base64_img.decode('ascii')  # finally, decode it to ascii characters
#
#         return base64_ascii_img
