import json
import logging
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from traffic_monitor.views import video_views, chart_views
from traffic_monitor.models.model_monitor import Monitor, MonitorFactory
from traffic_monitor.models.model_feed import FeedFactory
from traffic_monitor.models.model_detector import Detector
from traffic_monitor.services.monitor_service import MonitorService, ActiveMonitorServices

logger = logging.getLogger('api')


def get_class_data(request, monitor_id):
    """
    Get class data including class_name, class_id, is_mon_on and is_log_on

    :param request:
    :param monitor_id:
    :return:
    """

    class_data = video_views.get_class_data(request, monitor_id)
    class_data = {c['class_id']: {'class_name': c['class_name'],
                                  'class_id': c['class_name'].replace(' ', '_'),
                                  'is_monitoring': c['is_monitoring'],
                                  'is_logging': c['is_logging']} for c in class_data}

    return JsonResponse(class_data, safe=False)


def toggle_box(request):
    """

    :param request:
    :return:
    """

    divid = request.body.decode()
    divid = dict(json.loads(divid))

    action = divid.get('action')
    class_id = divid.get('class_id')
    monitor_id = int(divid.get('monitor_id'))
    print(action, class_id, monitor_id)

    rv = video_views.toggle_box(action, class_id, monitor_id)

    print(rv)

    return HttpResponse(rv)


def toggle_all(request, monitor_id, action):
    logger.info(f"TOGGLE ALL: {action} - {monitor_id}")
    rv = video_views.toggle_all(monitor_id=monitor_id, action=action)

    logger.info(rv)

    return HttpResponse(rv)


def get_active_monitors(request):
    active_monitors = video_views.get_active_monitors()

    rv = {m_id: {'id': m_id,
                 'detector': m.detector.detector_id,
                 'feed': m.feed.description} for m_id, m in active_monitors.items()}

    return JsonResponse(rv, safe=False)


def get_streams(request):
    """
    Return a dictionary of all available video streams.

    :param request:  HTML Request. (not used for this function)
    :return: A JsonResponse dictionary of video streams. {stream: {'cam': , 'time_zone': , 'url': ,'description': }}
    """

    rv = FeedFactory().getall()

    if not rv['success']:
        return JsonResponse(rv, safe=False)

    rv = {s['cam']: s for s in rv.get('feeds').values()}

    return JsonResponse(rv, safe=False)


def get_detectors(request):
    """
    Return a dictionary of all available detectors.

    :param request:  HTML Request. (not used for this function)
    :return: A JsonResponse dictionary of detectors. {detector_id: {'id':, 'name': , 'model': }}
    """

    rv = Detector().getall()

    if not rv['success']:
        return JsonResponse({'success': False, 'message': rv['message']}, safe=False)

    rv = {d['detector_id']: d for d in rv.get('detectors').values()}

    return JsonResponse(rv, safe=False)


def get_monitors(request):
    rv = MonitorFactory().getall()

    if not rv['success']:
        return JsonResponse({'success': False, 'message': rv['message']}, safe=False)

    # active_monitors = video_views.get_active_monitors().keys()

    rv = {m['name']: m for m in rv.get('monitors').values()}

    return JsonResponse(rv, safe=False)


def get_monitor(request):
    name = request.GET.get('name')
    if name is None:
        return JsonResponse({'success': False, 'message': "'name' parameter is required.", 'monitor': None})

    obj = MonitorFactory().get(monitor_name=name)
    return JsonResponse(
        {'success': obj.get('success'),
         'monitor': f"{obj.get('monitor')}",
         'message': f"{obj.get('message')}"}, safe=False)


def create_monitor(request):
    """

    :param request: The HTML request that should include values for 'state', 'exclude_counties', 'top_n_counties' and 'data_type'.
    See the parameter descriptions below for constraints and defaults for each parameter.
    :return:
    """
    if request is not None:
        name = request.GET.get('name', None)
        detector_id = request.GET.get('detector_id', None)
        feed_cam = request.GET.get('feed_cam', None)

        obj = MonitorFactory().create(name=name, detector_id=detector_id, feed_cam=feed_cam)
        return JsonResponse(
            {'success': obj.get('success'), 'monitor': f"{obj.get('monitor')}", 'message': f"{obj.get('message')}"},
            safe=False)


def create_monitor_service(request):

    monitor_name = request.GET.get('monitor_name', None)
    if monitor_name is None:
        return JsonResponse({'success': False, 'message': "'monitor_name' is a required parameter", 'monitor_service': None}, safe=False)

    rv = MonitorFactory().get(monitor_name)
    if not rv['success']:
        return JsonResponse(rv, safe=False)
    else:
        monitor = rv.get('monitor')

    monitor_service = MonitorService(monitor=monitor, logged_objects=None, notified_objects=None)

    return JsonResponse({"success": True, 'monitor_service': f"{monitor_service}", 'message': "Monitor service successfully created."}, safe=False)


def get_monitor_services(request):
    monitor_services = MonitorService.get_instances()
    rv = {}
    for m_id in monitor_services.keys():
        i = MonitorService.get_instance(int(m_id))
        rv.update({m_id: {"id": i.id,
                          "name": i.name,
                          "monitor": f"{i.monitor}"}})

    return JsonResponse(rv, safe=False)


def get_monitor_service(request):
    monitor_id = request.GET.get('id', None)
    if monitor_id is None:
        return JsonResponse({"success": False, "message": "'id' is a required parameter.", "monitor_service": None})

    monitor_service: MonitorService = MonitorService.get_instance(int(monitor_id))
    if monitor_service is None:
        return JsonResponse({"success": False, "message": f"No instance with id '{monitor_id}'", "monitor_service": None})
    else:
        return JsonResponse({"success": True,
                             "message": "Successfully retrieved instance",
                             "monitor_service": {"id": monitor_service.id,
                                                 "name": monitor_service.name,
                                                 "monitor": f"{monitor_service.monitor}"}}, safe=False)


def get_trained_objects(request):
    monitor_id = request.GET.get('id', None)
    if monitor_id is None:
        return JsonResponse({"success": False, "message": "'id' is a required parameter.", "monitor_service": None})

    monitor_service: MonitorService = MonitorService.get_instance(int(monitor_id))
    if monitor_service is None:
        return JsonResponse({"success": False, "message": f"No instance with id '{monitor_id}'", "monitor_service": None})
    else:
        return JsonResponse(list(monitor_service.get_trained_objects()), safe=False)


def toggle_log_object(request):
    monitor_id = request.GET.get('id', None)
    if monitor_id is None:
        return JsonResponse({"success": False, "message": "'id' is a required parameter."})
    monitor_service: MonitorService = MonitorService.get_instance(int(monitor_id))
    if monitor_service is None:
        return JsonResponse(
            {"success": False, "message": f"No monitor instance with id '{monitor_id}'"})

    trained_objects = monitor_service.get_trained_objects()

    object_name = request.GET.get('object', None)
    if object_name is None:
        return JsonResponse({"success": False, "message": "'object' is a required parameter."})

    if object_name not in trained_objects:
        return JsonResponse({"success": False, "message": f"'{object_name}' is not a trained object."})

    rv = monitor_service.toggle_logged_object(object_name=object_name)

    return JsonResponse(rv, safe=False)


def toggle_notified_object(request):
    monitor_id = request.GET.get('id', None)
    if monitor_id is None:
        return JsonResponse({"success": False, "message": "'id' is a required parameter."})
    monitor_service: MonitorService = MonitorService.get_instance(int(monitor_id))
    if monitor_service is None:
        return JsonResponse(
            {"success": False, "message": f"No monitor instance with id '{monitor_id}'"})

    trained_objects = monitor_service.get_trained_objects()

    object_name = request.GET.get('object', None)
    if object_name is None:
        return JsonResponse({"success": False, "message": "'object' is a required parameter."})

    if object_name not in trained_objects:
        return JsonResponse({"success": False, "message": f"'{object_name}' is not a trained object."})

    rv = monitor_service.toggle_notified_object(object_name=object_name)

    return JsonResponse(rv, safe=False)


def get_logged_objects(request):
    monitor_id = request.GET.get('id', None)
    if monitor_id is None:
        return JsonResponse({"success": False, "message": "'id' is a required parameter."})
    monitor_service: MonitorService = MonitorService.get_instance(int(monitor_id))
    if monitor_service is None:
        return JsonResponse(
            {"success": False, "message": f"No monitor instance with id '{monitor_id}'"})

    return JsonResponse(list(monitor_service.get_logged_objects()), safe=False)


def get_notified_objects(request):
    monitor_id = request.GET.get('id', None)
    if monitor_id is None:
        return JsonResponse({"success": False, "message": "'id' is a required parameter."})
    monitor_service: MonitorService = MonitorService.get_instance(int(monitor_id))
    if monitor_service is None:
        return JsonResponse(
            {"success": False, "message": f"No monitor instance with id '{monitor_id}'"})

    return JsonResponse(list(monitor_service.get_notified_objects()), safe=False)


def start_monitor(request, monitor_id: int):
    print(f"starting: {monitor_id}")
    rv = ActiveMonitorServices().get(monitor_id)

    # no need to start monitor if it already exists
    if rv['success']:
        return JsonResponse({'success': False, 'message': f"Monitor {monitor_id} is already started."})

    # get monitor details from db - fail if monitor doesn't exist
    rv = Monitor.get(monitor_id)
    if not rv['success']:
        return JsonResponse({'success': False, 'message': rv['message']}, safe=False)

    monitor = rv.get('monitor')
    ms = MonitorService(detector_id=monitor.detector.detector_id, feed_cam=monitor.feed.cam)
    ms.start()

    return JsonResponse({'success': True, 'monitor_id': ms.monitor.id}, safe=False)


def stop_monitor(request, monitor_id: int):
    rv = ActiveMonitorServices().get(monitor_id)
    if not rv['success']:
        return JsonResponse({'success': False, 'message': rv['message']}, safe=False)

    ms = rv.get('monitor_service')
    ms.stop()

    return JsonResponse({'success': True, 'monitor_id': ms.monitor.id}, safe=False)


def get_chart(request, monitor_id: int, interval: int = 0):
    rv = chart_views.get_chart(monitor_id=monitor_id, interval=interval)
    return rv
