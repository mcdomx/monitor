import logging
import pafy
import cv2 as cv
import numpy as np

from django.db import models

logger = logging.getLogger('model')


class Feed(models.Model):
    cam = models.CharField(max_length=256, primary_key=True)
    time_zone = models.CharField(max_length=32)
    url = models.URLField()
    description = models.CharField(max_length=64)

    @staticmethod
    def get_url(cam: str) -> str:
        """
        Determine the true url of the video stream.
        Use YouTube url if not a local webcam.
        """

        # start by assuming that a url was passed in
        url = cam

        if type(url) is str and url.isdigit():
            url = int(url)

        # test video feed
        read_pass = Feed.test_cam(url)

        if read_pass:
            logger.info("Video Test       : OK")
            logger.info("Video FPS        : {}".format(Feed.get_camfps(url)))
            return url
        else:
            # if capture fails, try as YouTube Stream
            # https://pypi.org/project/pafy/

            logger.info("Searching for YouTube stream...")
            if '/' in url and 'youtube' in url:  # a full video path was given
                cam = url.split('/')[-1]
            try:
                video_pafy = pafy.new(cam)
            except Exception:
                raise Exception("No video stream found: {}".format(cam))

            # get most reasonably-sized stream h x w < 350k
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
            read_pass = Feed.test_cam(stream.url)

            if read_pass:
                url = stream.url
                logger.info("YouTube Video Stream Detected!")
                logger.info(f"Video Resolution : {stream.resolution}")
                logger.info(f"Video FPS        : {Feed.get_camfps(url)}")
                logger.info("Video Test       : OK")
            else:
                raise Exception("Tried as YouTube stream. Can't acquire video source: {}".format(cam))

        return url

        # # add feed to db or update it if it already exists
        # try:
        #     obj = Feed.objects.get(pk=cam)
        #     if obj:  # update
        #         setattr(obj, 'url', url)
        #         setattr(obj, 'description', cam)
        #         obj.save()
        #         logger.info(f"Updated feed with new url for: {cam}")
        #     else:  # create
        #         obj = Feed.objects.create(cam=cam, url=url, description=cam, time_zone=time_zone)
        #         obj.save()
        #         logger.info(f"Created new feed entry for: {cam}")
        #
        #     return url
        #
        # except Exception as e:
        #     logger.info(e)
        #     logger.info(f"ERR: ID: {cam}")
        #     logger.info(f"ERR: URL: {url}")

    @staticmethod
    def test_cam(cam: str) -> bool:
        try:
            cap = cv.VideoCapture(cam)
            read_pass = cap.grab()
            cap.release()
            if read_pass:
                return True
            else:
                return False
        except Exception as e:
            logger.info(e)
            return False


    @staticmethod
    def get_camfps(cam: str) -> float:
        """
        Return the camera's published FPS.
        """
        cap = cv.VideoCapture(cam)
        cam_fps = cap.get(cv.CAP_PROP_FPS)
        cap.release()

        return cam_fps


class FeedFactory:
    """
    FeedFactory is used to get feeds.
    If requested feed does not exist it is created and stored
    in application db.
    """
    singelton = None

    def __new__(cls):
        if cls.singelton is None:
            cls.singelton = cls._Singleton()
        return cls.singelton

    class _Singleton:
        def __init__(self):
            self.logger = logging.getLogger('feed_factory')
            self.monitors = {}

        def get(self, cam: str, time_zone: str = 'US/Eastern') -> dict:

            # see if cam already exists
            obj = Feed.objects.get(pk=cam)

            try:
                if obj is not None:  # cam exists but the url may have changed
                    url = Feed.get_url(cam)
                    setattr(obj, 'url', url)
                    obj.save()
                    logger.info(f"Updated feed with new url for: {cam}")

                else:  # cam doesn't exist, create a new db entry
                    url = Feed.get_url(cam=cam)
                    obj = Feed.objects.create(cam=cam, url=url, description=cam, time_zone=time_zone)
                    obj.save()
                    logger.info(f"Created new feed entry for: {cam}")

                return {'success': True, 'feed': obj}

            except Exception as e:
                return {'success': False, 'message': e}
