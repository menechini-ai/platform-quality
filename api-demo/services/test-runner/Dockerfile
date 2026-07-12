FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir httpx fastapi uvicorn litellm langgraph langchain-core 2>&1 | tail -3

COPY . .

EXPOSE 8003

CMD ["uvicorn", "services.test-runner.app:app", "--host", "0.0.0.0", "--port", "8003"]