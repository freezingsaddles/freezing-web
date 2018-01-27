# BUILD
# =====

FROM ubuntu:xenial as buildstep

COPY resources/docker/sources.list /etc/apt/sources.list
RUN apt-get update

RUN apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:jonathonf/python-3.6
RUN apt-get update

RUN apt-get install -y python3.6 python3.6-dev libmysqlclient-dev curl build-essential git

RUN mkdir -p /build/wheels
RUN curl https://bootstrap.pypa.io/get-pip.py | python3.6

RUN pip3 install --upgrade pip setuptools wheel

ADD requirements.txt /tmp/requirements.txt
#RUN pip wheel -r /tmp/requirements.txt --no-binary MySQL-python --wheel-dir=/build/wheels
RUN pip3 wheel -r /tmp/requirements.txt --wheel-dir=/build/wheels

ADD . /app
WORKDIR /app

RUN python3.6 setup.py bdist_wheel -d /build/wheels


# DEPLOY
# =====

FROM ubuntu:xenial as deploystep

COPY resources/docker/sources.list /etc/apt/sources.list

RUN apt-get update \
  && apt-get install -y software-properties-common curl \
  && add-apt-repository -y ppa:jonathonf/python-3.6 \
  && apt-get update \
  && apt-get install -y python3.6 libmysqlclient-dev vim-tiny --no-install-recommends \
  && apt-get clean \
  && curl https://bootstrap.pypa.io/get-pip.py | python3.6 \
  && pip3 install --upgrade pip setuptools wheel \
  && rm -rf /var/lib/apt/lists/*

# Place app source in container.
VOLUME /app/static

RUN mkdir -p /app
COPY freezing/web/static /app/static

WORKDIR /app

COPY --from=buildstep /build/wheels /tmp/wheels

RUN pip3 install /tmp/wheels/*

EXPOSE 8000

ENTRYPOINT gunicorn --bind 0.0.0.0:8000 'freezing.web.app'
