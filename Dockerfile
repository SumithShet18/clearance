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
WORKDIR /app/apps/api
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
