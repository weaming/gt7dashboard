# Build stage: install dependencies with uv (matching distroless Python 3.11)
FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY requirements.txt .

RUN uv pip install --no-cache --target /opt/deps -r requirements.txt

ADD https://raw.githubusercontent.com/ddm999/gt7info/web-new/_data/db/cars.csv db/cars.csv

# Runtime stage: minimal distroless image
FROM gcr.io/distroless/python3-debian12

WORKDIR /usr/src/app

COPY --from=builder /opt/deps /opt/deps
COPY --from=builder /app/db db
COPY . .

ENV PYTHONPATH="/opt/deps"

CMD ["-m", "bokeh", "serve", "."]
