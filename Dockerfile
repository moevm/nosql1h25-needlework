FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src /app

ENV MONGO_URL=mongodb://root:example@db:27017/embroidery_db?authSource=admin
ENV PYTHONPATH=/app

CMD ["uvicorn", "web_viewer:app", "--host", "0.0.0.0", "--port", "8000"]