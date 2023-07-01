
FROM python:3.9-slim-buster

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8000

CMD ["uwsgi", "--http", ":8000", "--wsgi-file", "SongSearchAPI/wsgi.py", "--static-map", "/static=/static"]