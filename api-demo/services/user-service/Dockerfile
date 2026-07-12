FROM python:3.12-slim

WORKDIR /app

# Install deps
COPY services/user-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY services/user-service/app.py .

# SQLite volume
VOLUME /data

EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]