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
    && apt-get clean

ADD . /var/opt/norduni/norduni

ADD docker/setup.sh /setup.sh
RUN /setup.sh

ADD docker/start.sh /start.sh

# Add Dockerfile to the container as documentation
ADD Dockerfile /Dockerfile

VOLUME ["/var/opt/norduni", "/var/log/norduni", "/var/opt/source"]

WORKDIR /

EXPOSE 8080

CMD ["bash", "/start.sh"]
