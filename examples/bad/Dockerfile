# Bad Dockerfile — intentionally triggers many DockRx rules
FROM python:3.13

WORKDIR /app

ENV API_SECRET=supersecret

ADD app.tar.gz /app

COPY . .

RUN pip install -r requirements.txt

RUN apt-get update && apt-get install -y curl

CMD ["python", "app.py"]
