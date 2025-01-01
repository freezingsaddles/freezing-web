FROM python:3.10-alpine
RUN apk update
RUN apk add py3-mysqlclient
RUN addgroup -S freezing && adduser -S -G freezing freezing
RUN pip3 install --upgrade pip
ADD . /app
RUN mkdir -p /data
COPY leaderboards /data/leaderboards
COPY alembic.ini /app
COPY pyproject.toml /app/
WORKDIR /app
RUN pip3 install .
ENV LEADERBOARDS_DIR=/data/leaderboards
USER freezing
EXPOSE 8000
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:8000", "freezing.web:app"]
