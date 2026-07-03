# AEGIS backend — multi-stage build, small final image, non-root user.
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /srv
COPY --from=builder /install /usr/local
COPY app ./app
RUN useradd --create-home aegis
USER aegis
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
