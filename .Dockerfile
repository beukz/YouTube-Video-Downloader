# Start from a Python base image (Debian/Ubuntu-based)
FROM python:3.11-slim

# Install FFmpeg via apt
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app code and run
COPY . /app
WORKDIR /app
CMD ["python", "app.py"]