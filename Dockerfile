FROM alpine:latest
LABEL authors="Markus Krogh <markus@nordu.net>"

RUN apk add --no-cache ca-certificates python2 py2-pip libpq

RUN pip install --upgrade pip
RUN mkdir /app
WORKDIR /app

#RUN apt-get update && \
#    apt-get -y dist-upgrade && \
#    apt-get install -y \
#      git \
#      build-essential \
#      libpython-dev \
#      python-pip \
#      python-virtualenv \
#      libpq-dev \
#      libffi-dev \
#      python-dev \
#    && apt-get clean
#
#ADD . /var/opt/norduni/norduni
#
#ADD docker/setup.sh /setup.sh
#RUN /setup.sh
#
#ADD docker/start.sh /start.sh
#
## Add Dockerfile to the container as documentation
#ADD Dockerfile /Dockerfile
#
#VOLUME ["/var/opt/norduni", "/var/log/norduni", "/var/opt/source"]
#
#WORKDIR /

ADD src /app
ADD requirements /app/requirements
RUN apk add --no-cache --virtual build-dependencies postgresql-dev musl-dev gcc python2-dev && \
      pip install -r requirements/dev.txt && pip install -r requirements/py2.txt && \
      apk del build-dependencies
ADD docker/alpine-start.sh /start.sh

EXPOSE 8000

ENTRYPOINT ["/start.sh"]
