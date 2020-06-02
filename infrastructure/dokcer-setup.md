Docker Setup

- Pull postgres docker image: <br>
`docker pull postgres`
- Setup `docker-compose` to include the database and user credentials.
- Run `docker-compose up`
- To restart: <br>
`docker-compose down` <br>
`docker volume remove monitor_data_db` <br>
Delete migrations <br>
`docker-compose up` <br>
`python manage.py makemigrations; python manage.py migrate` <br>
`python manage.py createsuperuser` <br>
`python manage.py setup_database`
