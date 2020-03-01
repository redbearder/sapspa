FROM python:3.7.5-alpine

WORKDIR /opt/backend

RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn pymysql
RUN flask db gunicorn
RUN flask db init
RUN flask db migrate
RUN flask db upgrade

ENV FLASK_APP sapspa.py

EXPOSE 23381



