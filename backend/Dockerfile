FROM python:3.11-slim

RUN pip install --no-cache-dir uv

WORKDIR /srv/capstone/backend

COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/app ./app
COPY data /srv/capstone/data

ENV PATH="/srv/capstone/backend/.venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
