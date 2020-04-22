FROM python:3.7-alpine
LABEL authors="Markus Krogh <markus@nordu.net>"

RUN apk add --no-cache ca-certificates
RUN apk --update add python3-dev libpq libxml2-dev libxslt-dev libffi-dev gcc musl-dev libgcc openssl-dev curl
RUN apk add jpeg-dev zlib-dev freetype-dev lcms2-dev openjpeg-dev tiff-dev tk-dev tcl-dev py-pillow
RUN pip3 install --upgrade pip
RUN mkdir /app
WORKDIR /app

ADD src /app
ADD requirements /app/requirements
RUN apk add --no-cache --virtual build-dependencies postgresql-dev musl-dev gcc python3-dev && \
      pip3 install -r requirements/dev.txt --index-url https://pypi.sunet.se/ && \
      apk del build-dependencies && \
      if [ ! -e /usr/bin/pip ]; then ln -s pip3 /usr/bin/pip ; fi && \
      if [[ ! -e /usr/bin/python ]]; then ln -sf /usr/bin/python3 /usr/bin/python; fi && \
      rm -r /root/.cache
ADD docker/alpine-start.sh /start.sh

EXPOSE 8000

ENTRYPOINT ["/start.sh"]
