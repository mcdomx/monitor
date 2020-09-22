import cv2 as cv
import base64
import io
import time
from PIL import Image
import numpy as np

from django.core.serializers.json import DjangoJSONEncoder
from django.http import JsonResponse

from traffic_monitor.models.feed_factory import FeedFactory
from traffic_monitor.websocket_channels import TestVideoChannel
from traffic_monitor.websocket_channels_factory import ChannelFactory

from django.shortcuts import render


def _parse_args(request, *args):
    """
    Helper function that will parse a series of args from a request.
    If an arg is not in the request, an exception is thrown.
    Arguments in the request that are not listed are included in the returned dictionary.
    :param request: The HTTP request that should contain the arguments
    :param args: A series of string values that represent the name of the argument
    :return: A dictionary where keys are the arguments and values the respective values of each argument.
    """

    rv = {}

    for arg_name in args:
        arg_value = request.GET.get(arg_name)
        if not arg_value:
            raise Exception(f"'{arg_name}' parameter is required.")
        rv.update({arg_name: arg_value})

    other_args = set(request.GET.keys()).difference(rv.keys())
    for other_name in other_args:
        rv.update({other_name: request.GET.get(other_name)})

    return rv


def index_view(request):
    # kwargs = _parse_args(request, 'monitor_name')
    kwargs = _parse_args(request)
    monitor_name = kwargs.get('monitor_name')
    if monitor_name is None:
        return render(request, 'traffic_monitor/selection_frame.html', kwargs)
    else:
        return render(request, 'traffic_monitor/monitor_frame.html', kwargs)


def create_monitor_view(request):
    return render(request, 'traffic_monitor/create_monitor_frame.html')


def create_feed_view(request):
    return render(request, 'traffic_monitor/create_feed_frame.html')


def test_video(request):
    kwargs = _parse_args(request, 'cam')
    cam = kwargs.get('cam')
    try:
        url = FeedFactory().get_url(cam)
        return JsonResponse({'success': True, 'message': 'Video stream available from URL.'}, safe=False)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Could not get video stream from URL. {e.args}'}, safe=False)

def _convert_imgarray_to_inmem_base64_jpg(img_array: np.array) -> base64:
    """
    ref: https://stackoverflow.com/questions/42503995/how-to-get-a-pil-image-as-a-base64-encoded-string
    Convert an image array into an in-memory base64 RGB image.
    The return value can be placed in an HTML src tag:
    <img src="data:image/jpg;base64,<<base64 encoding>>" height="" width="" alt="image">
    :param img_array: a numpy image
    :return: base64 image in ascii characters. The returned object can be placed in an <img> html tag's src (src="data:image/jpg;base64,<<return value>>")
    """
    # convert image from BGR to RGB
    img_array = img_array[:, :, ::-1]

    # create an in-memory rgb image from array using PIL library
    rgbimg = Image.fromarray(img_array, mode='RGB')

    b = io.BytesIO()  # create an empty byte object
    rgbimg.save(b, format='JPEG')  # save the rgb in-memory file to the object
    b.seek(0)  # move pointer back to the start of memory space
    img_bytes = b.read()  # read memory space into a new variable

    base64_img = base64.b64encode(img_bytes)  # encode the image to base64
    base64_ascii_img = base64_img.decode('ascii')  # finally, decode it to ascii characters

    return base64_ascii_img


def start_test_video_stream(request):
    kwargs = _parse_args(request, 'cam', 'channel_url')
    cam = kwargs.get('cam')
    channel_url = kwargs.get('channel_url')

    # set source of video stream
    try:
        url = FeedFactory().get_url(cam)
        cap = cv.VideoCapture(url)

        channel: TestVideoChannel = ChannelFactory().get(channel_url)
        if channel:
            while cap.isOpened():
                time.sleep(.03)
                success, frame = cap.read()
                if success:
                    msg = {'image': _convert_imgarray_to_inmem_base64_jpg(frame), 'shape': frame.shape}
                    channel.send(text_data=DjangoJSONEncoder().encode(msg))

        print("CHANNEL CLOSED")
        channel.close()

    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Could not get video stream from URL.'}, safe=False)



