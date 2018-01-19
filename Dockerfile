FROM python:3

ENV PYTHONUNBUFFERED 1
RUN mkdir /src
WORKDIR /src
COPY src /src

RUN pip3 install -r requirements.txt
