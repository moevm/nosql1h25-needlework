# Запуск чернового варианта

## Требования

```
pip install fastapi uvicorn motor python-multipart pymongo jinja2 python-multipart pillow
```

## Установка и запуск

1. **Запуск MongoDB в Docker**:

```bash
docker run -d --name mongodb -p 27017:27017 -v mongodb_data:/data/db mongo:latest
```
