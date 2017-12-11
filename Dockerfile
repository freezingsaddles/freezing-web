# BUILD
# =====

FROM ubuntu:xenial as buildstep

COPY resources/docker/sources.list /etc/apt/sources.list
RUN apt-get update
RUN apt-get install -y software-properties-common

RUN add-apt-repository -y ppa:jonathonf/python-3.6
RUN apt-get update
RUN apt-get install -y python3.6 python3.6-dev libmysqlclient-dev curl build-essential

RUN mkdir -p /build/wheels
RUN curl https://bootstrap.pypa.io/get-pip.py | python3.6
RUN python3.6 -m pip install --upgrade pip setuptools wheel

ADD requirements.txt /tmp/requirements.txt
#RUN pip wheel -r /tmp/requirements.txt --no-binary MySQL-python --wheel-dir=/build/wheels
RUN pip3.6 wheel -r /tmp/requirements.txt --wheel-dir=/build/wheels

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
  && python3.6 -m pip install --upgrade pip setuptools wheel \
  && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /config
RUN mkdir -p /data

VOLUME /config
VOLUME /data

# Place app source in container.
COPY . /app
WORKDIR /app

COPY --from=buildstep /build/wheels /tmp/wheels

RUN pip install /tmp/wheels/*

# Install app symlinks (this works better right now than python setup.py install,
# since there are some scripts that assume they are running from app directory.)
RUN python3.6 setup.py develop

EXPOSE 5000

ENV BAFS_SETTINGS=/config/settings.cfg

# There are lots of uses for this image, so we don't specify an entrypoint.
# Available commands are basically any of the scripts:
# bafs-init-db
# bafs-sync
# bafs-sync-detail
# bafs-sync-streams
# bafs-sync-photos
# bafs-sync-weather
# bafs-sync-athletes
# bafs-server

# ENTRYPOINT bafs-server
