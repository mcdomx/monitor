

from django.db import models


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
        return f"{rv}"
