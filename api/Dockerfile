FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928 AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv==0.5.24 && \
    uv export --no-dev --no-hashes -o requirements.txt && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.15-slim@sha256:65a65fc7b30b06cb6df4930fd4650697cb23f4c2698ab81fc87e4b031bc36928
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src ./src

RUN useradd --uid 1001 --create-home appuser
USER 1001

ENV PORT=8080
EXPOSE 8080

# The probe reads PORT from the environment so it always targets the port
# uvicorn actually binds to (PaaS platforms such as Fly.io and Render inject PORT).
HEALTHCHECK --interval=30s --timeout=4s --start-period=5s --retries=3 \
    CMD python -c "import os, httpx; httpx.get('http://localhost:' + os.environ.get('PORT', '8080') + '/healthz', timeout=3).raise_for_status()"

CMD ["sh", "-c", "exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
