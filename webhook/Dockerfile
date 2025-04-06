FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y default-mysql-client && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir pymysql

COPY . .

EXPOSE 3001

CMD ["python", "main.py"]
