# SOTO Agent — production container image.
#
# Build context = repo root (so COPY soto_agent/... resolves).
# Driven by `make image` (which runs `make prep` first to refresh the glossary
# copy + rebuild the vault subset under soto_agent/data/).
#
#   make -C soto_agent image
#
# Local smoke test before pushing:
#   docker build -f soto_agent/Dockerfile -t soto-agent:local .
#   docker run --rm -p 8000:8000 --env-file .env soto-agent:local

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    VAULT_PATH=/app/soto_agent/data/vault \
    GLOSSARY_PATH=/app/soto_agent/data/ubiquitous-language.md

# Install deps first so layer is cached between code-only changes.
COPY soto_agent/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Application code + baked data (vault subset + glossary).
COPY soto_agent/ /app/soto_agent/

EXPOSE 8000

CMD ["uvicorn", "soto_agent.server:app", "--host", "0.0.0.0", "--port", "8000"]
