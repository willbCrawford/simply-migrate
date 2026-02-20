# pull official base image
FROM python:3.11.2-slim-buster
LABEL authors="will-crawford"

# set work directory
WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-cache

# Copy the application into the container.
COPY app/ ./app

# Install the application dependencies.
WORKDIR /app

CMD ["uv", "run", "simply-migrate", "api"]