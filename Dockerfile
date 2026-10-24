FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV SINAL_ABERTO_HOST=0.0.0.0

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sinal_aberto ./sinal_aberto

EXPOSE 8000

CMD ["python", "-m", "sinal_aberto.server"]
