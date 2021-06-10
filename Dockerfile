FROM python:3.9.5-buster

WORKDIR vaccipy

ADD . .

RUN python -m pip install -r requirements.txt

ENTRYPOINT python3 main.py search -f kontaktdaten.json -r
