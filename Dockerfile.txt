FROM python:3.9

ENV APP_HOME /app
WORKDIR $APP_HOME

RUN apt-get update && apt-get install -y tzdata \
    libgdal-dev

RUN pip install --upgrade pip
RUN pip install pygdal=="`gdal-config --version`.*"
RUN pip install fiona

CMD ["python", "/app/create.py"]