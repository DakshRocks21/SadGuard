FROM python:3.10-slim
RUN apt-get update && apt-get install -y procps net-tools bash iptables curl
RUN apt-get install tcpdump -y

WORKDIR /app

ENV PYTHONPATH="${PYTHONPATH}:/app"

COPY . /app
RUN pip install --no-cache-dir -r requirements.txt pytest mitmproxy

ENV DEFAULT_CMD="pytest -v tests/test_app.py" 

COPY .sadguard/wrapper.sh /app/.sadguard/wrapper.sh
RUN chmod +x /app/.sadguard/wrapper.sh


ENTRYPOINT ["/bin/sh", "/app/.sadguard/wrapper.sh"]