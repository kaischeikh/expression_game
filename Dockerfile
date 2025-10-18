# syntax=docker/dockerfile:1.7-labs
FROM python:3.11-slim

ENV UV_LINK_MODE=copy \
    OLLAMA_HOST=http://host.docker.internal:11434

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN uv pip install --system --no-cache .

CMD ["expression-game"]
