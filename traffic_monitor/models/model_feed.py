import logging
import pafy
import cv2
import numpy as np

from django.db import models

logger = logging.getLogger('model')


class Feed(models.Model):
    id = models.CharField(max_length=256, primary_key=True)
    time_zone = models.CharField(max_length=32)
    url = models.URLField()
    description = models.CharField(max_length=64)

    @staticmethod
    def get_stream_url(cam: str, time_zone: str) -> (str, str):
        """
        Determine the true url of the video stream.
        Use YouTube url if not a local webcam.
        """

        # start by assuming that a url was passed in
        url = cam

        if type(url) is str and url.isdigit():
            url = int(url)

        # test video feed
        read_pass = Feed._test_cam(url)

        # if capture fails, try as YouTube Stream
        # https://pypi.org/project/pafy/
        if not read_pass:
            if '/' in url and 'youtube' in url:  # a full video path was given
                cam = url.split('/')[-1]
            try:
                video_pafy = pafy.new(cam)
            except Exception:
                raise Exception("No video stream found: {}".format(cam))
            # get most reasonable stream h x w < 350k
            res_limit = 105000

            # use pafy to get the url of the stream
            # find stream with resolution within res_limit
            logger.debug("Available stream sizes:")
            for s in video_pafy.streams:
                logger.debug(f"\t{s}")

            stream_num = 0
            for i, stream in enumerate(video_pafy.streams):
                x, y = np.array(stream.resolution.split('x'), dtype=int)
                if x * y < res_limit:
                    stream_num = i
                else:
                    break

            stream = video_pafy.streams[stream_num]
            logger.debug(f"Selected stream: {video_pafy.streams[stream_num]}")

            # test new stream from pafy
            read_pass = Feed._test_cam(stream.url)

            if read_pass:
                url = stream.url
                logger.info("YouTube Video Stream Detected!")
                logger.info("Video Resolution : {}".format(stream.resolution))

        logger.info("Video Test       : {}".format("OK" if read_pass else "FAIL - check that streamer is publishing"))

        if not read_pass:
            raise Exception("Can't acquire video source: {}".format(cam))

        # add feed to db or update it if it already exists
        try:
            obj = Feed.objects.get(pk=cam)
            if obj:  # update
                setattr(obj, 'url', url)
                setattr(obj, 'description', cam)
                obj.save()
                logger.info(f"Updated feed with new url for: {cam}")
            else:  # create
                obj = Feed.objects.create(id=cam, url=url, description=cam, time_zone=time_zone)
                obj.save()
                logger.info(f"Created new feed entry for: {cam}")

            return url, obj.id

        except Exception as e:
            logger.info(e)
            logger.info(f"ERR: ID: {cam}")
            logger.info(f"ERR: URL: {url}")



    @staticmethod
    def _test_cam(cam: str) -> bool:
        cap = cv2.VideoCapture(cam)
        read_pass = cap.grab()
        cap.release()

        if not read_pass:
            return False

        return True

    @staticmethod
    def get_camfps(cam: str) -> float:
        """
        Return the camera's published FPS.
        """
        cap = cv2.VideoCapture(cam)
        cam_fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()

        return cam_fps

