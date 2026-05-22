FROM python:3.12-slim

WORKDIR /app

COPY services/order/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/shared /app/shared
COPY services/order /app/order

ENV PYTHONPATH=/app

CMD ["uvicorn", "order.app:app", "--host", "0.0.0.0", "--port", "8001"]
