Traffic Monitor
===============

This application is designed to monitor a video stream and detect objects in it. Detections are recorded in a database so that they can be used to observe frequency of objects over time. This data can be used to train a model which can predict traffic patterns.

Logging and Monitoring
----------------------
The application supports two distinct types of activities for each type of object detected in the video stream; Logging and Monitoring.  Logging is the action of storing the counts of detected objects in the video stream.  The resulting log can be used to analyze traffic patterns.  Monitoring will trigger an action when a defined object is detected in the video stream.  For example, if an elephant is detected, a message can be sent or the frame image can be saved. (Currently, monitoring actions are not setup and intended for a future release.)

Logging and monitoring are separate and one can be set for an object without the other.


Architecture
------------
The application uses Django to publish pages and handle API requests.  A Postgres database is used to store configuration information as well as data collected by the Monitor.  In an effort to structure the application so that it can later be converted to a series of microservices, the Postgres database will run in a Docker container.

The application employs a concept of a Monitor which is a user-named combination of a Video Feed and a Detector.  The video feed is the link to the video source and the Detector is a configured object which includes an object detector which will detect objects in a video feed.  3 services are defined which independently perform actions based on the Monitor:

#. Monitor Service
This is the primary service that is necessary for any other service to operate.  The Monitor Service will initiate the video stream and perform detections.  The Monitor Service will store information that it calculates in queues.  These queues are used by other services to get information from the Monitor Service.

The monitor service runs as a thread, so an instantiated service is a one-time object.  Once the thread is stopped, it cannot be restarted and will be destroyed.  A new instance of the service is instantiated each time the service is restarted.

#. Log Service
The Log Service will pull the data from a Monitor Service that has been placed in logging queue and store the logged data into the application's database. Logged data can be used later to create models which can predict future appearance of objects or simply used to identify traffic patterns.

#. Chart Service
The Chart Service will collect data from the Monitor Service and publish a chart that displays the number of detected instances over time.

#. Notification Service (future)
The Notification service will perform a notification action (alert, email, text message, etc) based on the presence of a particular object detected in the video stream.  Where logging will record each instance of a detected object, the Notification Service will broadcast a notification the moment that an object is detected.  This service can be used as an 'alarm' or 'alert'; for example, if there is an elephant in your front yard.

In order to used a service with a Montitor, an instance of the service's class can be instantiated with a reference to the Monitor.  The Monitor and its services use queues to communicate as well as an Observer pattern.


Environment Setup
-----------------
The application relies on a ``.env`` file in the root.  This file supports the following environment variables:

*optional variables:*
::

    export VERBOSITY=DEBUG
    export log_interval=60  # seconds between logging traffic (default is 60 if not set here)

*required variables:*
::
    export DB_NAME=monitor_db  # name of database
    export DB_USER=monuser  # username of database
    export DB_PASSWORD=password  # user password of database
    export DB_HOST=0.0.0.0  # IP address of database (0.0.0.0 for Docker)
    export DJANGO_SECRET_KEY='<<gobblty_snobblty>>'  # Django secret key (can be anything)

The variables defined in the `.env` file will be included in the environment available in Django and accessible using:

::

    local_variable_name = os.getenv("<env_varibale_name>", "<default_if_not_found")


Database
--------

The application relies on a Postgres database. The default SQlite
database used by Django does not allow concurrent read/write requests
which can happen in this application.

Start Docker Postgres Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

-  Ensure you have the latest Postgres Docker image:

::

    docker pull postgres

-  To start container, run the following from the project’s
   ``infrastructure`` directory:

::

    docker-compose up

-  This will use the postgres image to create a docker container. If the
   container has previously been created, the container will be opened
   with the respective data stored in it.

Initialize Database
^^^^^^^^^^^^^^^^^^^

-  Run the following Django commands to setup the database from the project root directory:

::

    python manage.py migrate

    python manage.py createsuperuser

    python manage.py setup_database

Stop the Database Container
^^^^^^^^^^^^^^^^^^^^^^^^^^^

-  Run the following from the ``infratructure`` directory:

::

    docker-compose down

Delete Database
^^^^^^^^^^^^^^^

::

   docker-compose down
   docker volume remove infrastructure_monitor_data

-  Delete all migrations in the ``migrations`` directory:

::

    docker-compose up
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py setup_database

Change Database Settings and Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

-  Update variables and values in the ``docker-compose.yaml`` file in
   the ``infrastructure`` directory.
