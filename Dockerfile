# syntax=docker/dockerfile:1.7-labs
ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim as base

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1
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

# Install requirements
RUN uv pip install --system --no-cache .

# Expose the port that the application listens on.
EXPOSE 8000

# Run the application.
CMD streamlit run src/games/app/streamlit_app.py --server.headless=true --server.address=0.0.0.0 --server.port=8000
