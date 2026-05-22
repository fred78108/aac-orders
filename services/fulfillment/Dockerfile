FROM python:3.12-slim

WORKDIR /app

COPY services/fulfillment/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/shared /app/shared
COPY services/fulfillment /app/fulfillment

ENV PYTHONPATH=/app

CMD ["uvicorn", "fulfillment.app:app", "--host", "0.0.0.0", "--port", "8004"]
