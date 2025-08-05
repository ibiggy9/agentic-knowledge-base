#TODO: Make this better optimized for cloud run/artifact rego

FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

CMD ["python", "app.py"]