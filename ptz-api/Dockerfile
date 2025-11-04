FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir fastapi uvicorn[standard] onvif-zeep pydantic-settings

WORKDIR /app
COPY app.py /app/app.py

EXPOSE 8088
CMD ["uvicorn", "app:api", "--host", "0.0.0.0", "--port", "8088"]
