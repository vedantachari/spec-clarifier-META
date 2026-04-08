FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY spec_clarifier_scaffold.py .
COPY inference.py .
COPY openenv.yaml .

ENV PYTHONUNBUFFERED=1

CMD ["python", "inference.py"]
