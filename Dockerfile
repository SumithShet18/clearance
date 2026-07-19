FROM python:3.12-slim

WORKDIR /app
COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/api/requirements.txt

COPY apps /app/apps
COPY samples /app/samples
COPY evals /app/evals
COPY mcp-servers /app/mcp-servers
COPY data /app/data

ENV PYTHONPATH=/app/apps/api
ENV CLEARANCE_MODE=mock
WORKDIR /app/apps/api
# Render sets $PORT; default 8000 for local docker
ENV PORT=8000
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
