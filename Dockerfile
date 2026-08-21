FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv==0.5.24 && \
    uv export --no-dev --no-hashes -o requirements.txt && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src ./src

RUN useradd --uid 1001 --create-home appuser
USER 1001

ENV PORT=8080
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=4s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/healthz', timeout=3).raise_for_status()"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
