FROM python:3.11-slim
WORKDIR /app
COPY apps/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY simulator /app/simulator
COPY apps/api /app/apps/api
ENV PYTHONPATH=/app/apps/api:/app
CMD ["python", "simulator/service.py"]
