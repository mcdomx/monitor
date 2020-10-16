FROM python:3.7
ENV VERBOSITY=DEBUG
ENV PYTHONUNBUFFERED=1


#ENV DB_NAME=monitor_db
#ENV DB_USER=monuser
#ENV DB_PASSWORD=password
#ENV DB_HOST=0.0.0.0
#ENV DB_PORT=5432
#ENV DJANGO_SECRET_KEY="=bb+h=u9v)z-&3rqlzfet8$7&ybq46\$t1=33-\$_xm0)u1b+(in"

RUN mkdir /code
WORKDIR /code
COPY requirements.txt /code/
RUN pip install -r requirements.txt

COPY . /code/
