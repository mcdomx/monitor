FROM python:3.7
ENV VERBOSITY=DEBUG
ENV PYTHONUNBUFFERED=1

#RUN mkdir /code
#WORKDIR /code
#COPY requirements.txt /code/
#RUN pip install -r requirements.txt
#
#COPY . /code/

RUN mkdir /forecasting_service
WORKDIR /forecasting_service
COPY requirements.txt /forecasting_service
RUN pip install -r requirements.txt

COPY manage.py /forecasting_service/
COPY app /forecasting_service/app/
COPY forecasting_service /forecasting_service/forecasting_service/

#COPY . /code/
