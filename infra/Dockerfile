# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update -y && \
    apt-get install -y --no-install-recommends ffmpeg ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first (leverage layer cache)
COPY requirements.txt ./
COPY requirements ./requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY app ./app

ENV PORT=8080 \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=8080

EXPOSE 8080

CMD ["python", "-m", "app.main"]

