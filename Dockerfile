FROM python:3.7
ENV VERBOSITY=DEBUG
ENV PYTHONUNBUFFERED=1

RUN mkdir /app
WORKDIR /app
COPY Pipfile /app/Pipfile
COPY Pipfile.lock /app/Pipfile.lock

RUN pip install --upgrade pip
RUN pip install pipenv
RUN set -ex && PIP_USER=1 pipenv install --system --deploy -v

RUN apt-get update
RUN apt-get install 'ffmpeg' 'libsm6' 'libxext6' -y

RUN mkdir -p /root/.cvlib/object_detection/yolo/yolov3
WORKDIR /root/.cvlib/object_detection/yolo/yolov3
RUN wget -c https://github.com/pjreddie/darknet/raw/master/cfg/yolov3-tiny.cfg
RUN wget -c https://pjreddie.com/media/files/yolov3-tiny.weights
RUN wget -c https://github.com/arunponnusamy/object-detection-opencv/raw/master/yolov3.cfg
RUN wget -c https://pjreddie.com/media/files/yolov3.weights
RUN wget -c -O yolov3_classes.txt https://github.com/arunponnusamy/object-detection-opencv/raw/master/yolov3.txt

WORKDIR /app

COPY manage.py /app/
COPY monitor /app/monitor/
COPY traffic_monitor /app/traffic_monitor/
