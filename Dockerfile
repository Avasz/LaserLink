FROM python:3.9-slim

# Install system dependencies required for Bluetooth
# bluez is often needed for the stack interactions
RUN apt-get update && apt-get install -y \
    bluez \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/
COPY config.yaml .

# Run the application
CMD ["python3", "src/monitor.py"]
