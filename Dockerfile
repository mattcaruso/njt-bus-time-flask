FROM python:3.9.19-slim

COPY requirements/common.txt requirements/common.txt
RUN pip install -U pip && pip install -r requirements/common.txt

COPY ./api /app/api
COPY ./bin /app/bin
COPY wsgi.py /app/wsgi.py
WORKDIR /app

RUN useradd njt
USER njt

EXPOSE 8080

ENTRYPOINT ["bash", "/app/bin/run.sh"]