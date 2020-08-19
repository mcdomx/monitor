import logging
import pafy
import cv2 as cv
import numpy as np

from django.db import models

logger = logging.getLogger('model')


class Feed(models.Model):
    """
    A Feed is a represents a video feed.
    Since Feeds can be built during run-time, a FeedFactory should be used to
    create and retrieve Feed objects.
    """
    cam = models.CharField(max_length=256, primary_key=True)
    time_zone = models.CharField(max_length=32)
    url = models.URLField(max_length=1024)
    description = models.CharField(max_length=64)

    def __str__(self):
        rv = self.__dict__
        try:
            del rv['_state']
        except KeyError:
            pass
        return f"{rv}"


class FeedFactory:
    """
    FeedFactory is a Singleton used to get feeds and feed information.
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
            read_pass = FeedFactory().test_cam(url)

            if read_pass:
                logger.info("Video Test       : OK")
                logger.info("Video FPS        : {}".format(FeedFactory().get_camfps(url)))
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
                read_pass = FeedFactory().test_cam(stream.url)

                if read_pass:
                    url = stream.url
                    logger.info("YouTube Video Stream Detected!")
                    logger.info(f"Video Resolution : {stream.resolution}")
                    logger.info(f"Video FPS        : {FeedFactory().get_camfps(url)}")
                    logger.info("Video Test       : OK")
                else:
                    raise Exception("Tried as YouTube stream. Can't acquire video source: {}".format(cam))

            return url

        @staticmethod
        def test_cam(url: str) -> bool:
            try:
                cap = cv.VideoCapture(url)
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

        @staticmethod
        def getall() -> dict:
            try:
                feed_objs = Feed.objects.all()
                return {'success': True, 'feeds': feed_objs}
            except Exception:
                return {'success': False, 'message': f"Failed to retrieve feeds", 'feeds': None}

        @staticmethod
        def get(cam: str, time_zone: str = None) -> dict:
            """
            Returns a dict with 'success' and 'payload'.  If 'success' is False,
            payload is 'message'; if 'success is True, payload is 'feed' which
            contains a db Feed instance with (feed.cam, .timezone, .url, & .description)
            If a new feed is created, time_zone is required.

            """
            try:
                # see if cam already exists
                obj = Feed.objects.get(pk=cam)
                # cam exists but the url may have changed
                url = FeedFactory().get_url(cam)
                setattr(obj, 'url', url)
                obj.save()
                logger.info(f"Updated feed with new url for: {cam}")
                return {'success': True, 'feed': obj}

            except Feed.DoesNotExist as e:  # cam doesn't exist, create a new db entry
                if time_zone is None:
                    return {'success': False, 'message': 'New feed requires time_zone parameter.'}
                try:
                    url = FeedFactory().get_url(cam=cam)
                    obj = Feed.objects.create(cam=cam, url=url, description=cam, time_zone=time_zone)
                    obj.save()
                    logger.info(f"Created new feed entry for: {cam}")
                    return {'success': True, 'feed': obj}
                except Exception as e:
                    logger.error(e)
                    return {'success': False, 'message': e}
