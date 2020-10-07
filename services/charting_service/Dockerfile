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

COPY ./monitor_chart.py ./

EXPOSE ${BOKEH_PORT}

CMD bokeh serve --port ${BOKEH_PORT} \
    --allow-websocket-origin="*" \
    --disable-index \
    --disable-index-redirect \
    --num-procs=${NUM_PROCS} \
    --log-level=info \
    ./monitor_chart.py
