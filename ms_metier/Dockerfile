
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app
COPY ./ms_metier/pyproject.toml ./ms_metier/uv.lock ./
RUN uv sync --frozen --no-dev
COPY ./ms_metier .
COPY ./ms_data/data /ms_data/data

EXPOSE 8006

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8006", "--reload"]
