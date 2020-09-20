Traffic Monitor
===============

This application is designed to monitor a video stream and log the occurrence of detect objects in it. Detections are recorded in a database so that they can be used to analyze the frequency of objects over time. This data can be used to train a model which can predict patterns.

The application supports two distinct types of activities for each type of object detected in the video stream; Logging and Monitoring.

Logging
    Logging is the action of storing the counts of detected objects in the video stream.  The resulting log can be used to analyze traffic patterns.

Monitoring
    Monitoring will trigger an action when a defined object is detected in the video stream.  For example, if an elephant is detected, a message can be sent or the frame image can be saved. (Currently, monitoring actions are not setup and intended for a future release.)

A web font-end provides the most appealing and simple interface to the monitor but the monitor can also be controlled via rest calls and the progress can be seen in a terminal window.

Web Front-End
-------------
.. image:: ../docs_static/images/all_services.png
  :width: 600
  :alt: Home Screen

**Home**: Service activity is shown in separate sections.

.. image:: ../docs_static/images/monitor_configuration.png
  :width: 300
  :alt: Configuration

**Monitor Configuration**: (not shown in the screen shot above). The monitor configuration displays the current values used by the monitor.  As items are changed using the popup menus or via the API, these values are updated in the web page.

.. image:: ../docs_static/images/detector_service.png
  :width: 300
  :alt: Detector

**Detector**: Each detected image is displayed.  The popup menu is used to adjust detector sleep time and the level of confidence used.  Increasing sleep time will reduce the burden on the CPU.

.. image:: ../docs_static/images/chart_service.png
  :width: 300
  :alt: Chart

**Chart**: At each log interval the chart is updated.  The popup menu can be used to adjust the x-axis time horizon or the time zone that the time is displayed in.  Additionally, logged items can be toggled for inclusion in the charted values.

.. image:: ../docs_static/images/log_service.png
  :width: 300
  :alt: Log

**Log**: Logged items are presented with the most recently logged item first.  Items shown are items that have been added to the database.  Using the popup menu, logged items can be toggled and the interval used to log items to the database can be adjusted.

.. image:: ../docs_static/images/notification_service.png
  :width: 300
  :alt: Notification

**Notification**: Notified items are shown with the time that they were identified by the detector.  These items are not stored in the database.  The popup menu can be used to toggle the items that are presented in the notification log.

API
---
The application supports an API which can be used to setup, configure, start and stop monitors.  See the API documentation for details.

Architecture
------------
The application uses Django to publish pages and handle API requests.  A Postgres database is used to store configuration information as well as data collected by the Monitor.  In an effort to structure the application so that it can later be converted to a series of microservices, the Postgres database is run in a Docker container.

Communications
    Application components communicate across the backend using Kafka and the Django back-end communicates with web clients using WebSockets.

Services
    The application employs a concept of a Monitor which is a user-named combination of a Video Feed and a Detector.  The video feed is the link to the video source and the Detector is a configured object which includes an object detector which will detect objects in a video feed.  5 services are defined which are designed to operate independently:

1. Monitor Service
    This is the primary service that is necessary for any other service to operate.  The Monitor Service will initiate the video stream and other services that are configured for the monitor.  This service serves as the top-level coordinator for a Monitor and its supporting services.

    The monitor service runs as a thread, so an instantiated service is a one-time object.  Once the thread is stopped, it cannot be restarted and will be destroyed.  A new instance of the service is instantiated each time the service is restarted.  Configurations for the service are persistent and stored in the database, so new instances of the Monitor will have the same settings as the last time the monitor was used.

2. Video Detection Service
    This is the service that will capture images from a video stream and will deliver them to a Detector Machine where object detection is performed.  The application is designed so that this service can be replaced by another custom class that may perform detections on other sources of data such as an audio stream or a text stream.  The application currently only supports video detection.

    This Video Detection Service will start a Detector Machine which performs the work of extracting data from the video stream.

3. Log Service
    The Log Service will collect data from a detector through Kafka messages and subsequently store the logged data into the application's database. Logged data can be used later to create models which can predict future appearance of objects or simply used to identify traffic patterns.  A detector may be capable of detecting a long list of objects, but the Log Service can be configured to store a subset of items from the detector.  By default, the Log Service will write to the database each minute, but this frequency can be changed.

4. Chart Service
    The Chart Service will collect data from the Monitor Service and publish a chart to the web client that displays the number of detected instances over time.  The time zone and time horizon on the x-axis of this chart can be configured.

5. Notification Service (future)
    The Notification service will perform a notification action (alert, email, text message, etc) based on the presence of a particular object detected in the video stream.  Where logging will record each instance of a detected object, the Notification Service will broadcast a notification the moment that an object is detected.  This service can be used as an 'alarm' or 'alert'; for example, if there is an elephant in your front yard.

A small hierarchy of objects are necessary to organize data collected by a Monitor.  A Monitor is defined as a combination of a Video Feed and a Detector.  A Monitor is created by a user and given a unique name.  Data is retrieved via a reference to the Monitor.  The detector can be changed once a Monitor has been defined, but the monitor name and the video feed remain fixed.


Getting Started
===============

Environment Setup
-----------------

The application relies on a ``.env`` file in the root.  The creation of this file is simplified by running the following command:
::

    python manage.py create_env


This file supports the following environment variables:

*optional variables:*
::

    export VERBOSITY=INFO


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


Database and Kafka Messaging Services
-------------------------------------

The application relies on a Postgres database as well as Kafka for messaging. Postgres is used as the database because the default SQLite database used by Django does not allow concurrent read/write requests which can happen in this application.

Both the Postgres and Kafka services are configured to run in docker containers in this application.  To start the Docker containers, run the following from the project’s ``infrastructure`` directory:

::

    docker-compose up

Any data stored in these services will persist locally and will be available the next time that you start the containers from the same machine.

Alteratively, the database or kafka containers can be started individually; however, note that the application requires both to function:

::

    docker-compose up db

    docker-compose up zookeeper
    docker-compose up kafka

Initialize Database
^^^^^^^^^^^^^^^^^^^
The first time that you start the database, it will need to be initialized with Django.

-  Run the following Django commands to setup the database from the project root directory:

::

    python manage.py migrate
    python manage.py createsuperuser
    python manage.py setup_database

Stop the Database and Kafka Containers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To stop both the database and Kafka containers:

-  Run the following from the ``infratructure`` directory:

::

    docker-compose down

Alternatively, either service can be individually stopped:

::

    docker-compose down db

    docker-compose down kafka
    docker-compose down zookeeper

Delete Database
^^^^^^^^^^^^^^^
In the event that you want to delete the database and start over, follow the steps below.

::

   docker-compose down
   docker volume remove infrastructure_monitor_data

-  Delete all migrations in the ``migrations`` directory:

::

    docker-compose up
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py setup_database

Change Database and Kafka Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changes to the Postgres or Kafka services can be made by updating the docker-compose.yaml file:

-  Update variables and values in the ``docker-compose.yaml`` file in
   the ``infrastructure`` directory.


Start Application
-----------------
The application can be started via:

::

    python manage.py runserver

Using this command, the application will be published to http://127.0.0.1:8000

Alternatively, you can define the IP address and port used by the application.  If you set the IP address t the host computer's IP address, you will be able to access the application from any machine on the local network:

::

    python manage.py runserver 10.0.0.1:12345



