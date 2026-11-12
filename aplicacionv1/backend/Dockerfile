FROM python:3.12-slim AS builder
WORKDIR /app
RUN python -m venv /opt/venv
COPY backend/requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache
RUN /opt/venv/bin/python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

FROM python:3.12-slim
RUN useradd --create-home --uid 10001 exb
WORKDIR /app
ENV PATH=/opt/venv/bin:$PATH PYTHONPATH=/app PYTHONUNBUFFERED=1 TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /opt/tiktoken-cache /opt/tiktoken-cache
COPY backend/app app
COPY backend/scripts scripts
COPY backend/migrations migrations
COPY backend/alembic.ini .
USER exb
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
