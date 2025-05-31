# Použijme oficiální image s Pythonem a ffmpegem
FROM jrottenberg/ffmpeg:4.4-alpine as ffmpeg

FROM python:3.11-slim

# Nainstaluj potřebné nástroje
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
