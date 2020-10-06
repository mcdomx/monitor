docker build --tag charting_service .

docker run -it -p 8100:8080 --rm charting_service