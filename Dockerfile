FROM python:3.11-slim

# Install system dependencies if any are needed
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY controller/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Only the controller is baked into the image. Templates and values are fetched
# from the PR branch at provision time via the GitHub API.
COPY controller/ ./controller/

# Set Python path so it can find the modules
ENV PYTHONPATH=/app/controller

EXPOSE 8080
CMD ["uvicorn", "controller.main:app", "--host", "0.0.0.0", "--port", "8080"]