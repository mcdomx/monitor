import logging
from django.db import models


# from traffic_monitor.models.model_detector import Detector


# Create your models here.

class Class(models.Model):
    key = models.CharField(max_length=128, primary_key=True)
    class_name = models.CharField(max_length=64)
    class_id = models.CharField(max_length=64)
    detector_id = models.CharField(max_length=128)
    monitor = models.BooleanField(default=True)
    log = models.BooleanField(default=True)

    @staticmethod
    def create(class_name: str, detector_id: str, monitor: bool = True, log: bool = False):
        class_id = class_name.replace(' ', '_')
        key = f"{detector_id}__{class_id}"
        obj, success = Class.objects.update_or_create(key=key,
                                                      class_name=class_name,
                                                      class_id=class_id,
                                                      detector_id=detector_id,
                                                      monitor=monitor, log=log)
        obj.save()

    @staticmethod
    def toggle_all_mon(detector_id: str):
        logger = logging.getLogger('model')
        logger.info(f"toggling all monitored items: {detector_id}")

        try:
            rs = Class.objects.filter(detector_id=detector_id)
            set_value = True

            # if any are on, turn all off
            if rs.filter(monitor=True).count() > 0:
                set_value = False

            for r in rs:
                r.monitor = set_value
                r.save(update_fields=['monitor'])

        except Exception as e:
            return {'success': False, 'message': e}

        return {'success': True}

    @staticmethod
    def toggle_all_log(detector_id: str):
        try:
            rs = Class.objects.filter(detector_id=detector_id)

            set_value = True

            # if any are on, turn all off
            if rs.filter(log=True).count() > 0:
                set_value = False

            for r in rs:
                r.log = set_value
                r.save(update_fields=['log'])

        except Exception as e:
            return {'success': False, 'message': e}

        return {'success': True}

    @staticmethod
    def toggle_mon(class_id: str, detector_id: str):
        try:
            obj = Class.objects.get(detector_id=detector_id, class_id=class_id)
            if obj.monitor is True:
                obj.monitor = False
            else:
                obj.monitor = True
            obj.save(update_fields=['monitor'])
            return {'success': True}
        except Exception as e:
            return {'success': False, 'message': e}

    @staticmethod
    def toggle_log(class_id: str, detector_id: str):
        try:
            obj = Class.objects.get(detector_id=detector_id, class_id=class_id)
            if obj.log is True:
                obj.log = False
            else:
                obj.log = True
            obj.save(update_fields=['log'])
            return {'success': True}
        except Exception as e:
            return {'success': False, 'message': e}

    @staticmethod
    def get_class_data(detector_id: str):
        return Class.objects.filter(detector_id=detector_id).values()

    @staticmethod
    def get_monitored_objects(detector_id: str):
        rs = Class.objects.filter(detector_id=detector_id, monitor=True)
        return [c.class_id for c in rs]

    @staticmethod
    def get_logged_objects(detector_id: str):
        rs = Class.objects.filter(detector_id=detector_id, log=True)
        return [c.class_id for c in rs]
