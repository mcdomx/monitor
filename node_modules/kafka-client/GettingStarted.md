# Getting started

Running on ubuntu.
```
$ cat /etc/*release
DISTRIB_ID=Ubuntu
DISTRIB_RELEASE=17.10
DISTRIB_CODENAME=artful
DISTRIB_DESCRIPTION="Ubuntu 17.10"
```

I installed docker.

To get started I utilized the [karka-node](https://github.com/SOHU-Co/kafka-node) repository and cloned into a directory.  This provides docker compose script to spin up a zookeeper and kafka docker image.  
```
./start-docker.sh
```
This starts zookeeper on port 2181 and kafka on port 9092.
```
$ netstat -an  | grep
tcp6       0      0 :::9092                 :::*                  LISTEN
tcp6       0      0 :::9093                 :::*                  LISTEN
tcp6       0      0 :::2181                 :::*                  LISTEN  
```


It is possible to open a bash session in the docker container using the following command
```
docker ps  //to find the container ids

docker exec -i -t <container id> /bin/bash //to open a bash session in the container
```

The kafka bin directory has a number of shell scripts that allow for configuration.
```
cd /opt/kafka/bin

./kafka-topics.sh --list --zookeeper  <host vm interface>:2181  //To list topics
```
