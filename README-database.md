## Database
The application relies on a Postgres database.  Teh default SQlite database used by Django does not allow concurrent read/write requests which can happen in this application.

#### Start Docker Postgres Database
- Ensure you have the latest Postgres Docker image: <br>
`docker pull postgres`
- To start container, run the following from the project's `infrastructure` directory: <br>
`docker-compose up`
- This will use the postgres image to create a docker container.  If the container has previously been created, the container will be opened with the respective data stored in it.

#### Initialize Database
- run the following Django commands to setup the database from te project root directory: <br>
    - `python manage.py migrate`
    - `python manage.py createsuperuser` <br>
    - `python manage.py setup_database` <br>

#### Stop the Database Container
- run the following from the `infratructure` directory:<br>
`docker-compose down`

#### Delete Database
- `docker-compose down`
- `docker volume remove monitor_data_db`
- Delete all migrations in the `migrations` directory <br>
- `docker-compose up` <br>
- `python manage.py migrate` <br> 
- `python manage.py createsuperuser` <br>
- `python manage.py setup_database` <br>

#### Change Database Settings and Configuration
- update variables and values in the `docker-compose.yaml` file in the `infrastructure` directory.
