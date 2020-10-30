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

COPY manage.py /app/
COPY monitor /app/monitor/
COPY traffic_monitor /app/traffic_monitor/
