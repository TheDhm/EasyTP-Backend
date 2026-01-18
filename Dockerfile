FROM python:3.14-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Tell uv to create the venv outside /app so COPY doesn't overwrite it
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        libxml2-dev \
        libxslt1-dev \
        libjpeg-dev \
        zlib1g-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Python dependencies
COPY pyproject.toml uv.lock /app/
RUN uv sync --frozen --no-dev

# Copy project
COPY . /app/

RUN mkdir -p /READONLY /USERDATA /app/media

# Create non-root user with explicit UID 1000 (matches securityContext)
RUN groupadd --gid 1000 app \
    && useradd --uid 1000 --gid 1000 --create-home --shell /bin/bash app \
    && chown -R app:app /app /opt/venv
USER app

# Expose port
EXPOSE 8000

COPY --chmod=+x entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]