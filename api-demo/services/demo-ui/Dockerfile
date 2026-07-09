FROM python:3.12-slim

WORKDIR /app

# Minimal deps for the demo UI
RUN pip install --no-cache-dir fastapi uvicorn httpx ddtrace

COPY services/demo-ui/app.py .

EXPOSE 8004

CMD ["ddtrace-run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8004"]