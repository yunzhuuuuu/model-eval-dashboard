FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY worker-requirements.txt .
RUN pip install --no-cache-dir \
        torch==2.14.0+cpu \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r worker-requirements.txt

COPY evaluation_core ./evaluation_core
COPY worker ./worker

CMD ["python", "-m", "worker"]
