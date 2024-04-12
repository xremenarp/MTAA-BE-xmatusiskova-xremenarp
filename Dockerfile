FROM python:3.12-slim

# System setup
RUN apt update -y
RUN apt install -y libpq-dev

COPY . .
RUN pip3 install -r requirements.txt --no-cache-dir

EXPOSE 8000

CMD hypercorn app.__main__:app --reload

