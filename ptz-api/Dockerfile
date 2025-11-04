FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# system libs sometimes needed by zeep/SOAP/wsdl
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 && rm -rf /var/lib/apt/lists/*

COPY app.py ./

ENV API_HOST=0.0.0.0
ENV API_PORT=8088

EXPOSE 8088
CMD ["uvicorn", "app:api", "--host", "0.0.0.0", "--port", "8088"]
