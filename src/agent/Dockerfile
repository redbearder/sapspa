FROM python:3.7.5-alpine

WORKDIR /opt/agent

RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install uwsgi

ENV FLASK_APP sapspa_agent.py

EXPOSE 23310



