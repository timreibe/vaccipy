FROM python:3.9.5-buster

WORKDIR vaccipy

RUN apt-get update && apt-get install -y jq

ADD . .

RUN python -m pip install -r requirements.txt

RUN chmod +x ./wait-for-google-chrome.sh

ENTRYPOINT ./wait-for-google-chrome.sh python3 main.py search -f kontaktdaten.json -r
