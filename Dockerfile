FROM openjdk:17-slim

# Python kurulumu
RUN apt-get update && apt-get install -y python3 python3-pip && apt-get clean

# Çalışma dizini
WORKDIR /app

# Gereksinimler
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Kodları kopyala
COPY . .

# Port ayarı
ENV PORT 5000
EXPOSE 5000

# Start komutu
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
