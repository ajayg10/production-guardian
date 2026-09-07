FROM python:3.11-slim
WORKDIR /app
COPY apps/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY apps/api /app/apps/api
COPY simulator /app/simulator
ENV PYTHONPATH=/app/apps/api:/app
EXPOSE 8000
WORKDIR /app/apps/api
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
