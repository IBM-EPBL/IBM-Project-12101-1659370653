FROM python:3.7-slim

ENV PYTHONUNBUFFERED 1

WORKDIR /app

COPY . /app
COPY ./requirements.txt /requirements.txt

RUN pip install -r requirements.txt --no-cache-dir 

RUN export FLASK_APP='app.py'


CMD [ "flask","run", "--host=0.0.0.0","--port=5000"]

EXPOSE 5000
