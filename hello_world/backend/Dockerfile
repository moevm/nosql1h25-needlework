FROM python:3.11

COPY requirements.txt backend/requirements.txt

RUN pip install -r backend/requirements.txt

WORKDIR /backend

COPY . .

CMD ["fastapi", "run", "main.py", "--port", "8000"]