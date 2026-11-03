FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.lock /workspace/backend/requirements.lock
RUN pip install --no-cache-dir -r backend/requirements.lock
COPY backend /workspace/backend
RUN useradd --create-home explainpay && mkdir -p /workspace/backend/storage /workspace/data/models \
    && chown -R explainpay:explainpay /workspace
USER explainpay
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
