from django.http import StreamingHttpResponse

def gen_stream():

    log_data = {}

    while True:


        yield log_data

def log_feed(request):
    """Log streaming route."""

    return StreamingHttpResponse(gen_stream(), content_type="multipart/x-mixed-replace;boundary=frame")
