#!/bin/bash
python src/init.py
python src/insert.py
exec uvicorn src.web_viewer:app --host 0.0.0.0 --port 8081
