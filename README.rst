Traffic Monitor
=================================

This application is designed to monitor a video stream and detect objects in it. Detections are recorded in a database so that they can be used to observe frequency of objects over time. This data can be used to train a model which can predict traffic patterns.

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

-  Run the following Django commands to setup the database from te
   project root directory:

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
   docker volume remove monitor_data_db

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
