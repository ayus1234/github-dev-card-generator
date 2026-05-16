FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application source
COPY . .

# Create static directory for cards
RUN mkdir -p frontend/cards

# Set working directory to backend to run uvicorn
WORKDIR /app/backend

# Expose the backend port
EXPOSE 8080

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
