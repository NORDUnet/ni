FROM ubuntu:15.10

MAINTAINER lundberg <lundberg@nordu.net>

ENV DEBIAN_FRONTEND noninteractive

RUN /bin/echo -e "deb http://se.archive.ubuntu.com/ubuntu wily main restricted universe\ndeb http://archive.ubuntu.com/ubuntu wily-updates main restricted universe\ndeb http://security.ubuntu.com/ubuntu wily-security main restricted universe" > /etc/apt/sources.list

RUN apt-get update && \
    apt-get -y dist-upgrade && \
    apt-get install -y \
      git \
      build-essential \
      libpython-dev \
      python-pip \
      python-virtualenv \
      libpq-dev \
      libffi-dev \
      python-dev \
      python-gunicorn \
    && apt-get clean

RUN mkdir -p /var/opt/norduni
RUN mkdir -p /var/log/norduni
RUN mkdir -p /var/opt/src

VOLUME ["/var/opt/norduni", "/var/log/norduni", "/var/opt/src"]

ADD setup.sh /setup.sh
RUN /setup.sh

ADD start.sh /start.sh

# Add Dockerfile to the container as documentation
ADD Dockerfile /Dockerfile

WORKDIR /

EXPOSE 8080

CMD ["bash", "/start.sh"]
