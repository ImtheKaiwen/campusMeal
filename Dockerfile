FROM python:3.13-slim

# Java kur
RUN apt-get update && apt-get install -y openjdk-17-jdk && apt-get clean

# Çalışma dizini
WORKDIR /app

# Gereksinimler
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodları kopyala
COPY . .

# Port ayarı
ENV PORT 5000
EXPOSE 5000

# Start komutu
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
