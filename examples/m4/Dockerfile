# Build only from locally reviewed project source. For production pin the base image by digest.
FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi==0.115.12 httpx==0.28.1
COPY backend /app/backend
COPY examples /app/examples
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app
# The operator's runner overrides the entrypoint to call backend.app.research.m4_worker.
CMD ["python", "-m", "backend.app.research.m4_worker"]
