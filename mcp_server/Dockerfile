FROM python:3.13-slim

WORKDIR /app

COPY mcp_server/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY mcp_server ./mcp_server
COPY fastapi ./fastapi

WORKDIR /app

EXPOSE 8002

CMD ["python", "mcp_server/server.py"]