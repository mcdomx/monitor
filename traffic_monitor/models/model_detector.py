
from django.db import models


class Detector(models.Model):
    """
    Detector is a database model class that represents the detector_machines available in the application.
    Since detector_machines are static and only created at build-time, no Detector Factory is necessary.
    """
    detector_id = models.CharField(max_length=128, primary_key=True)
    name = models.CharField(max_length=64)
    model = models.CharField(max_length=64)

    def __str__(self):
        rv = self.__dict__
        return f"{rv}"

    @staticmethod
    def getall() -> dict:
        try:
            det_objs = Detector.objects.all()
            return {'success': True, 'detector_machines': det_objs}
        except Exception as e:
            return {'success': False, 'message': f"Failed to retrieve detector_machines"}
