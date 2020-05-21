import json
import logging
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie

from traffic_monitor.views import video_views


def get_class_data(request, detector_id):
    """ Get class data including class_name, class_id, is_mon_on and is_log_on"""

    class_data = video_views.get_class_data(detector_id)
    class_data = {c['class_id']: {'class_name': c['class_name'],
                                 'class_id': c['class_name'].replace(' ', '_'),
                                 'monitor': c['monitor'],
                                 'log': c['log']} for c in class_data}

    return JsonResponse(class_data, safe=False)


def toggle_box(request):
    divid = request.body.decode()
    divid = dict(json.loads(divid))

    action = divid.get('action')
    class_id = divid.get('class_id')
    detector_id = divid.get('detector_id')
    print(action, class_id, detector_id)

    rv = video_views.toggle_box(action, class_id, detector_id)

    print(rv)

    return HttpResponse(rv)


def toggle_all(request, detector_id, action):
    # divid = request.body.decode()
    # divid = dict(json.loads(divid))
    #
    # action = divid.get('action')
    # detector_name = divid.get('detector')

    logger = logging.getLogger('django')

    logger.info(f"TOGGLE ALL: {action} - {detector_id}")
    rv = video_views.toggle_all(detector_id=detector_id, action=action)
    logger.info(rv)

    return HttpResponse(rv)
