FROM python:3.7-slim

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV BOKEH_RESOURCES=cdn

RUN apt-get update \
    && apt-get install gcc -y \
    && apt-get install git -y \
    && apt-get clean

WORKDIR /app

COPY ./requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

ENV NUM_PROCS=4
ENV BOKEH_URL='127.0.0.1'
ENV BOKEH_PORT=8080
ENV DATA_URL='host.docker.internal'
ENV DATA_PORT=8000

EXPOSE ${BOKEH_PORT}
COPY ./monitor_chart.py ./
#EXPOSE ${BOKEH_PORT}

CMD bokeh serve --port ${BOKEH_PORT} \
    --allow-websocket-origin="*" \
    --disable-index \
    --disable-index-redirect \
    --num-procs=${NUM_PROCS} \
    --log-level=debug \
    ./monitor_chart.py
