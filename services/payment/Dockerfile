FROM python:3.12-slim

WORKDIR /app

COPY services/payment/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/shared /app/shared
COPY services/payment /app/payment

ENV PYTHONPATH=/app

CMD ["uvicorn", "payment.app:app", "--host", "0.0.0.0", "--port", "8002"]
