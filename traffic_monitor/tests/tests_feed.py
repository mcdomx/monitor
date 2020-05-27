import logging
from django.test import TestCase

from traffic_monitor.models.model_feed import FeedFactory, Feed

# Create your tests here.

logger = logging.getLogger('test')


class FeedTestCase(TestCase):
    def setUp(self):
        cam = '1EiC9bvVGnk'
        time_zone = 'US/Mountain'
        url = Feed.get_url(cam)
        obj = Feed.objects.create(cam=cam, url=url, description=cam, time_zone=time_zone)
        obj.save()

    def test_create_youtube_url(self):
        """ Test that a URL can be created"""
        logger.info("TESTING CREATE YOUTUBE URL")
        cam = '1EiC9bvVGnk'
        try:
            url = Feed.get_url(cam)
            self.assertIsNotNone(url)

        except Exception as e:
            self.assertTrue(False)

    def test_create_url(self):
        """ Test that a URL can be created"""
        logger.info("TESTING CREATE RAW URL")
        cam = '1EiC9bvVGnk'
        try:
            url = Feed.get_url(cam)
            _ = Feed.get_url(url)
            self.assertTrue(True)
        except Exception as e:
            self.assertTrue(False)

    def test_create_feed(self):
        logger.info("TESTING CREATE FEED ")
        cam_stream = '1EiC9bvVGnk'
        cam_stream_timezone = 'US/Mountain'
        rv_dict = FeedFactory().get(cam=cam_stream, time_zone=cam_stream_timezone)
        self.assertTrue(rv_dict.get('success'))

    def test_retrieve_feed(self):
        logger.info("TESTING RETRIEVE FEED FROM DB")
        cam_stream = '1EiC9bvVGnk'
        cam_stream_timezone = 'US/Mountain'
        rv = FeedFactory().get(cam=cam_stream, time_zone=cam_stream_timezone)
        self.assertTrue(rv['success'])

    def test_get_image_from_feed(self):
        logger.info("TESTING RETRIEVE FEED FROM DB")
        cam_stream = '1EiC9bvVGnk'
        cam_stream_timezone = 'US/Mountain'
        rv = FeedFactory().get(cam=cam_stream, time_zone=cam_stream_timezone)
        feed = rv.get('feed')
        test_result = Feed.test_cam(feed.url)
        self.assertTrue(test_result)

