# syntax=docker/dockerfile:1
FROM python:3.8

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

WORKDIR /app/src/

CMD ["python", "process.py", "-s", "csv"]