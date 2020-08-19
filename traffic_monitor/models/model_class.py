# import logging
# from django.db import models
#
#
# from traffic_monitor.models.model_monitor import Monitor
#
# logger = logging.getLogger('model')
#
#
# class Class(models.Model):
#     """
#     Stores all the classes that a monitor has the capability of identifying
#     as well as whether or not they are currently set to be logged or notified.
#     """
#     class_name = models.CharField(max_length=64)
#     class_id = models.CharField(max_length=64)
#     monitor = models.ForeignKey(Monitor, on_delete=models.CASCADE, null=True)
#     is_notifying = models.BooleanField(default=True)
#     is_logging = models.BooleanField(default=True)
#
#     @staticmethod
#     def create(class_name: str, monitor: Monitor):
#         """ Create db entry for classes.  If already exists, don't change logging and monitoring status. """
#         obj, success = Class.objects.update_or_create(class_name=class_name,
#                                                       class_id=class_name.replace(' ', '_'),
#                                                       monitor=monitor)
#         obj.save()
#
#     @staticmethod
#     def toggle_all_notifications(monitor: Monitor):
#         logger.info(f"toggling all notified items: {monitor}")
#
#         try:
#             rs = Class.objects.filter(monitor=monitor)
#             set_value = True
#
#             # if any are on, turn all off
#             if rs.filter(is_notifying=True).count() > 0:
#                 set_value = False
#
#             for r in rs:
#                 r.is_notifying = set_value
#                 r.save(update_fields=['is_notifying'])
#
#         except Exception as e:
#             return {'success': False, 'message': e}
#
#         return {'success': True}
#
#     @staticmethod
#     def toggle_all_log(monitor: Monitor):
#         try:
#             rs = Class.objects.filter(monitor=monitor)
#
#             set_value = True
#
#             # if any are on, turn all off
#             if rs.filter(is_logging=True).count() > 0:
#                 set_value = False
#
#             for r in rs:
#                 r.is_logging = set_value
#                 r.save(update_fields=['is_logging'])
#
#         except Exception as e:
#             return {'success': False, 'message': e}
#
#         return {'success': True}
#
#     @staticmethod
#     def toggle_not(class_id: str, monitor: Monitor):
#         try:
#             obj = Class.objects.get(monitor=monitor, class_id=class_id)
#             if obj.is_notifying is True:
#                 obj.is_notifying = False
#             else:
#                 obj.is_notifying = True
#             obj.save(update_fields=['is_notifying'])
#             return {'success': True}
#         except Exception as e:
#             return {'success': False, 'message': e}
#
#     @staticmethod
#     def toggle_log(class_id: str, monitor: Monitor):
#         try:
#             obj = Class.objects.get(monitor=monitor, class_id=class_id)
#             if obj.is_logging is True:
#                 obj.is_logging = False
#             else:
#                 obj.is_logging = True
#             obj.save(update_fields=['is_logging'])
#             return {'success': True}
#         except Exception as e:
#             return {'success': False, 'message': e}
#
#     @staticmethod
#     def get_class_data(monitor: Monitor):
#         return Class.objects.filter(monitor=monitor).values()
#
#     @staticmethod
#     def get_notified_objects(monitor: Monitor):
#         rs = Class.objects.filter(monitor=monitor, is_notifying=True)
#         return [c.class_id for c in rs]
#
#     @staticmethod
#     def get_logged_objects(monitor: Monitor):
#         rs = Class.objects.filter(monitor=monitor, is_logging=True)
#         return [c.class_id for c in rs]
