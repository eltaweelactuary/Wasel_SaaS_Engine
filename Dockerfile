FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Security: run as non-root user
RUN useradd -m waseluser
USER waseluser

EXPOSE 8080
ENV PORT=8080

# Gunicorn with eventlet worker for WebSocket support + timeout for long connections
CMD exec gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:$PORT --timeout 120 engine:app
