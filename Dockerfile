# pull official base image
FROM python:3.11.2-slim-buster
LABEL authors="lily-pad"

# set work directory
WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy the application into the container.
COPY . /app

# Install the application dependencies.
WORKDIR /app
RUN uv sync --locked --no-cache

RUN ls -latr

CMD ["uv", "run", "fastapi", "dev", "--host", "0.0.0.0"]