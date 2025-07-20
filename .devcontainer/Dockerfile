# Use official Python image as base
FROM mcr.microsoft.com/vscode/devcontainers/python:3.11

# Install system packages (GDAL, PostgreSQL client, etc.)
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get install -y gdal-bin libgdal-dev postgresql-client \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install pip packages from requirements.txt (if it exists)
COPY requirements.txt /tmp/pip-tmp/
RUN pip install --upgrade pip && pip install -r /tmp/pip-tmp/requirements.txt && rm -rf /tmp/pip-tmp