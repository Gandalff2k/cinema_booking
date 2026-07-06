FROM python:3.11-slim

WORKDIR /home/app

RUN apt-get update \
    && apt-get install -y gcc libpq-dev python3-dev build-essential \
    && rm -rf /var/lib/apt/lists/*
    
RUN pip install --upgrade pip poetry

COPY pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-root --no-interaction --no-ansi

COPY . .