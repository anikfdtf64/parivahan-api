# Base image already has Chromium + all deps preinstalled
FROM mcr.microsoft.com/playwright/python:v1.54.0-jammy

# Workdir inside the container
WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app (app.py etc.)
COPY . .

# Uvicorn will listen on this port
ENV PORT=8000
EXPOSE 8000

# Start FastAPI server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
